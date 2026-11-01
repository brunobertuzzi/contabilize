// Declarações globais para bibliotecas externas carregadas via CDN e extensões do Window

declare namespace bootstrap {
  class Toast {
    constructor(element: HTMLElement | null, options?: Record<string, unknown>);
    show(): void;
    hide(): void;
    dispose(): void;
    static getInstance(element: HTMLElement | null): Toast | null;
  }

  class Modal {
    constructor(element: HTMLElement | null, options?: Record<string, unknown>);
    show(): void;
    hide(): void;
    dispose(): void;
    static getInstance(element: HTMLElement | null): Modal | null;
  }
}

declare class Chart {
  constructor(context: HTMLCanvasElement | CanvasRenderingContext2D, config: Record<string, unknown>);
  destroy(): void;
  update(): void;
  data: Record<string, unknown>;
}

interface Window {
  bootstrap?: typeof bootstrap;
  Chart?: typeof Chart;
  SPED_DEBUG?: boolean;
  empresaSelecionada?: boolean;
  sugestoesPendentes?: import('./sped').SugestaoClassificacao[];
  showToast: (message: string, type?: import('./common').ToastType) => void;
  showConfirmModal: (message: string, onConfirm?: () => void) => void;
  showSpinner: () => void;
  hideSpinner: () => void;
  formatDate: (date: Date) => string;
  formatCurrency: (value: number) => string;
  loadCfops: () => Promise<void>;
  saveCfop: () => Promise<void>;
  editCfop: (codigo: string) => Promise<void>;
  deleteCfop: (codigo: string) => Promise<void>;
  loadAcumuladores: () => Promise<void>;
  saveAcumulador: (event?: Event) => Promise<void>;
  editAcumulador: (codigo: string) => Promise<void>;
  deleteAcumulador: (codigo: string) => Promise<void>;
  loadProdutos: (page?: number) => Promise<void>;
  deleteProduto: (codigo: string) => Promise<void>;
  loadVendas: (page?: number) => Promise<void>;
  loadVendasReport: () => void;
  loadCfopReport: () => Promise<void>;
  loadCompetencias: () => Promise<void>;
  loadAllReports: () => Promise<void>;
  toggleDetalhes: (index: number) => void;
  abrirModalClassificacao: () => Promise<void>;
  aprovarSugestaoModal: (codigoItem: string, acumulador: string) => Promise<void>;
  rejeitarSugestaoModal: (codigoItem: string) => void;
  aprovarTodasSugestoes: () => Promise<void>;
  aprovarSugestao: (codigoItem: string, acumulador: string) => Promise<void>;
  rejeitarSugestao: (codigoItem: string) => void;
  analisarInconsistencias: () => Promise<void>;
  trocarAcumuladorInconsistencia: (codigoProduto: string, novoAcumulador: string, index: number) => Promise<void>;
  ignorarInconsistencia: (index: number) => void;
}
