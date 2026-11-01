// Tipos utilitários compartilhados entre os módulos da aplicação

export type ToastType = 'success' | 'danger' | 'warning' | 'info';

export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  error?: string;
  data?: T;
  [key: string]: unknown;
}

export interface PaginationResult<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
