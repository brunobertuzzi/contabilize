"""
Analisador de Produtos por Similaridade
=======================================

Este módulo classifica produtos sugerindo acumuladores com base na
similaridade com produtos já cadastrados no banco de dados.
"""

import difflib
import logging
import re
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

from scripts.database import Acumulador, ProdutoSped, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductAnalyzer:
    """Analisador de produtos usando similaridade de string (Fuzzy Matching)."""

    def __init__(self):
        pass

    def _listar_acumuladores(self) -> List[Dict]:
        """Lista todos os acumuladores disponíveis."""
        with get_db() as db:
            acumuladores = db.query(Acumulador).all()
            return [
                {"codigo": a.codigo, "descricao": a.descricao} for a in acumuladores
            ]

    def _encontrar_similar(
        self,
        produto_desc: str,
        produto_ncm: str,
        referencias: List[Tuple[str, str, str]],
    ) -> Optional[Tuple[str, str]]:
        """
        Encontra o acumulador do produto mais similar na lista de referências.
        referencias: lista de (descricao, ncm, codigo_acumulador).
        """
        if not referencias:
            return None

        melhor_score = 0
        melhor_acumulador = None
        descricao_produto_similar = ""

        # Normaliza descrição e NCM do produto alvo
        produto_desc = produto_desc.upper()
        produto_ncm = re.sub(r"\D", "", str(produto_ncm or ""))  # Apenas dígitos
        tokens_prod = set(produto_desc.split())

        for ref_desc, ref_ncm, ref_acum in referencias:
            score = 0

            # --- Fator 1: Descrição (0.0 a 1.0) ---
            ratio = difflib.SequenceMatcher(None, produto_desc, ref_desc).ratio()

            # Token overlap check
            tokens_ref = set(ref_desc.split())
            if tokens_prod and tokens_ref:
                common = tokens_prod.intersection(tokens_ref)
                if len(common) >= 2 or (len(common) == 1 and len(list(common)[0]) > 4):
                    overlap_ratio = len(common) / min(len(tokens_prod), len(tokens_ref))
                    if overlap_ratio >= 0.5:
                        ratio = max(ratio, 0.70)

            score = ratio

            # --- Fator 2: NCM Boosting (Add up to 0.3) ---
            ref_ncm = re.sub(r"\D", "", str(ref_ncm or ""))
            if produto_ncm and ref_ncm:
                if produto_ncm == ref_ncm:
                    score += 0.3  # Boost forte para NCM exato
                elif (
                    len(produto_ncm) >= 4
                    and len(ref_ncm) >= 4
                    and produto_ncm[:4] == ref_ncm[:4]
                ):
                    score += 0.15  # Boost médio para Capítulo/Posição igual

            if score > melhor_score:
                melhor_score = score
                melhor_acumulador = ref_acum
                descricao_produto_similar = ref_desc

        # Threshold ajustado (considerando que NCM pode ter subido o score)
        # Se NCM bateu (boost 0.3), precisa de apenas 0.3 de texto (muito pouco)
        # Vamos exigir um mínimo de texto OU um score total alto

        if melhor_score >= 0.60:
            # Garante que o score não ultrapasse 100%
            score_display = min(melhor_score, 1.0)
            return (
                melhor_acumulador,
                f"Similaridade ({int(score_display * 100)}%) com: {descricao_produto_similar}",
            )

        return None

    def analisar_produtos_sem_acumulador(self, limite: int = 50) -> List[Dict]:
        """
        Analisa produtos sem acumulador usando comparação com base existente.
        """
        try:
            with get_db() as db:
                # 1. Busca produtos sem acumulador
                produtos = (
                    db.query(ProdutoSped)
                    .filter(ProdutoSped.acumulador_id.is_(None))
                    .limit(limite)
                    .all()
                )

                if not produtos:
                    return []

                # 2. Busca base de referência (produtos JÁ classificados)
                # Adiciona NCM na query
                produtos_referencia = (
                    db.query(ProdutoSped)
                    .filter(ProdutoSped.acumulador_id.isnot(None))
                    .limit(2000)
                    .all()
                )

                # Prepara lista de referências normalizada: (desc, ncm, acum)
                refs = [
                    (
                        p.descricao_item.upper(),
                        p.ncm,
                        p.acumulador_rel.codigo if p.acumulador_rel else None,
                    )
                    for p in produtos_referencia
                    if p.acumulador_rel
                ]

                logger.info(
                    f"Analisando {len(produtos)} produtos contra {len(refs)} referências..."
                )

                resultados = []

                for produto in produtos:
                    acumulador = None
                    motivo = "Sem referência similar"

                    if refs:
                        res = self._encontrar_similar(
                            produto.descricao_item, produto.ncm, refs
                        )
                        if res:
                            acumulador, motivo = res

                    resultados.append(
                        {
                            "codigo_item": produto.codigo_item,
                            "descricao": produto.descricao_item[:50],
                            "ncm": produto.ncm,
                            "acumulador_sugerido": acumulador,
                            "motivo": motivo,
                        }
                    )

                return resultados

        except Exception as e:
            logger.error(f"Erro na análise de produtos: {e}", exc_info=True)
            return []

    def sugerir_acumulador(
        self, produto: SimpleNamespace, acumuladores: Optional[List[Dict]] = None
    ) -> Tuple[Optional[str], str]:
        """
        Sugere acumulador para um único produto (wraps logic).
        """
        try:
            with get_db() as db:
                produtos_referencia = (
                    db.query(ProdutoSped)
                    .filter(ProdutoSped.acumulador_id.isnot(None))
                    .limit(2000)
                    .all()
                )
                refs = [
                    (
                        p.descricao_item.upper(),
                        p.ncm,
                        p.acumulador_rel.codigo if p.acumulador_rel else None,
                    )
                    for p in produtos_referencia
                    if p.acumulador_rel
                ]

                if not refs:
                    return None, "Sem base de conhecimento"

                res = self._encontrar_similar(
                    produto.descricao_item, getattr(produto, "ncm", ""), refs
                )
                if res:
                    return res
                return None, "Sem similaridade suficiente"

        except Exception as e:
            logger.error(f"Erro ao sugerir acumulador individual: {e}")
            return None, f"Erro: {str(e)}"

    def analisar_inconsistencias(self, limite: int = 100) -> List[Dict]:
        """
        Analisa produtos com NCM igual E descrições similares (>=80%) mas acumuladores diferentes.
        Útil para identificar classificações inconsistentes.

        Otimizado: agrupa por NCM primeiro para evitar comparações O(n²) desnecessárias.
        """
        try:
            with get_db() as db:
                # Busca produtos que já têm acumulador
                produtos = (
                    db.query(ProdutoSped)
                    .filter(ProdutoSped.acumulador_id.isnot(None))
                    .limit(2000)
                    .all()
                )

                if len(produtos) < 2:
                    return []

                # Agrupa produtos por prefixo NCM (4 primeiros dígitos) para reduzir comparações
                from collections import defaultdict

                ncm_groups = defaultdict(list)

                for p in produtos:
                    ncm_norm = re.sub(r"\D", "", str(p.ncm or ""))  # Apenas dígitos
                    ncm_prefix = ncm_norm[:4] if len(ncm_norm) >= 4 else ncm_norm

                    ncm_groups[ncm_prefix].append(
                        {
                            "codigo": p.codigo_item,
                            "descricao": p.descricao_item,
                            "descricao_norm": p.descricao_item.upper().strip(),
                            "ncm": p.ncm,
                            "ncm_norm": ncm_norm,
                            "acumulador": p.acumulador_rel.codigo
                            if p.acumulador_rel
                            else None,
                        }
                    )

                inconsistencias = []

                # Só compara dentro do mesmo grupo NCM (muito mais eficiente)
                for ncm_prefix, grupo in ncm_groups.items():
                    if len(grupo) < 2:
                        continue

                    # Compara apenas produtos dentro do mesmo grupo NCM
                    for i, prod1 in enumerate(grupo):
                        for prod2 in grupo[i + 1 :]:
                            # Só compara se acumuladores são diferentes
                            if prod1["acumulador"] == prod2["acumulador"]:
                                continue

                            # Verifica NCM mais precisamente
                            ncm1, ncm2 = prod1["ncm_norm"], prod2["ncm_norm"]
                            ncm_igual = ncm1 == ncm2

                            # Calcula similaridade da descrição
                            ratio = difflib.SequenceMatcher(
                                None, prod1["descricao_norm"], prod2["descricao_norm"]
                            ).ratio()

                            # Considera inconsistência se descrição >= 80% similar
                            if ratio >= 0.80:
                                inconsistencias.append(
                                    {
                                        "produto1_codigo": prod1["codigo"],
                                        "produto1_descricao": prod1["descricao"][:60],
                                        "produto1_ncm": prod1["ncm"],
                                        "produto1_acumulador": prod1["acumulador"],
                                        "produto2_codigo": prod2["codigo"],
                                        "produto2_descricao": prod2["descricao"][:60],
                                        "produto2_ncm": prod2["ncm"],
                                        "produto2_acumulador": prod2["acumulador"],
                                        "similaridade": int(ratio * 100),
                                        "ncm_igual": ncm_igual,
                                    }
                                )

                                if len(inconsistencias) >= limite:
                                    break

                        if len(inconsistencias) >= limite:
                            break

                    if len(inconsistencias) >= limite:
                        break

                # Ordena por similaridade decrescente
                inconsistencias.sort(key=lambda x: x["similaridade"], reverse=True)

                logger.info(f"Encontradas {len(inconsistencias)} inconsistências")
                return inconsistencias

        except Exception as e:
            logger.error(f"Erro na análise de inconsistências: {e}", exc_info=True)
            return []
