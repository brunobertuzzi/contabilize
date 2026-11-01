// Modelos e interfaces do domínio fiscal SPED

export interface Empresa {
  id: number;
  cnpj: string;
  razao_social: string;
  nome_fantasia?: string;
  inscricao_estadual?: string;
  uf?: string;
}

export interface Cfop {
  id?: number;
  cfop: string;
  descricao?: string;
}

export interface Acumulador {
  id?: number;
  codigo: string;
  descricao: string;
  cfop?: string;
  cfop_id?: number;
}

export interface ProdutoSped {
  id?: number;
  codigo_item: string;
  descricao_item: string;
  unidade: string;
  ncm: string;
  acumulador?: string;
  acumulador_id?: number;
  aliquota_icms?: number;
  cest?: string;
  cod_barras?: string;
}

export interface SugestaoClassificacao {
  codigo_item: string;
  descricao_item: string;
  ncm: string;
  acumulador_sugerido: string;
  produto_referencia?: string;
  score_similaridade?: number;
}

export interface InconsistenciaNcm {
  ncm: string;
  produto1_codigo: string;
  produto1_descricao: string;
  produto1_acumulador: string;
  produto2_codigo: string;
  produto2_descricao: string;
  produto2_acumulador: string;
}

export interface ItemVenda {
  num_documento: string;
  data: string;
  codigo_item: string;
  descricao_item: string;
  quantidade: number;
  valor_total: number;
  acumulador?: string;
}

export interface VendasReportResponse {
  vendas: ItemVenda[];
  total_itens: number;
  total_valor: number;
  total_paginas: number;
  pagina_atual: number;
}
