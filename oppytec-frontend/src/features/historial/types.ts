// oppytec-frontend/src/features/historial/types.ts
/**
 * Tipos de movimiento canónicos del Kardex auditables.
 * Alineados 100% con la especificación de dominio y backend.
 */
export type TipoMovimiento =
  | "all"
  | "conteo"
  | "consumo"
  | "merma"
  | "ajuste"
  | "transferencia"
  | "compra"
  | "entrada"
  | "salida"
  | "reversion"
  | "redo"
  | "ajuste_auditoria";

/**
 * Registro individual enriquecido del libro mayor de auditoría e historial del Kardex.
 */
export interface RegistroMovimiento {
  id: string | number;
  producto_id: string | number;
  cantidad: number;
  tipo_movimiento: string;
  motivo_merma: string | null;
  usuario_id: number;
  created_at: string;
  bodega_id: string | number;
  descripcion_merma: string | null;
  lote_codigo?: string | null;
  fecha_vencimiento?: string | null;
  fecha_vencimiento_lote?: string | null;
  fecha_recuento: string;
  user_display_name?: string;
  nombre_producto?: string;
  nombre_bodega?: string;
  unidad_medida?: string;
  costo_unitario_ppp?: number;
  costo_total_movimiento?: number;
  saldo_resultante?: number;
  transfer_id?: string | null;
  delta_before?: number | null;
  delta_after?: number | null;
}

/**
 * Producto catalogado para selector de insumos en Historial.
 */
export interface HistorialCatalogProduct {
  id: string | number;
  nombre: string;
  unidad: string;
}

/**
 * Alias de compatibilidad histórica para `Producto`.
 */
export type Producto = HistorialCatalogProduct;

/**
 * Contrato de estado de filtros multi-criterio.
 */
export interface HistorialFilters {
  filtroProducto: string;
  setFiltroProducto: (id: string) => void;
  filtroTipo: TipoMovimiento;
  setFiltroTipo: (tipo: TipoMovimiento) => void;
  fechaDesde: Date | undefined;
  setFechaDesde: (date: Date | undefined) => void;
  fechaHasta: Date | undefined;
  setFechaHasta: (date: Date | undefined) => void;
  filtroUsuario: string;
  setFiltroUsuario: (usuario: string | ((prev: string) => string)) => void;
  clearFilters: () => void;
}

/**
 * Contrato de paginación server-side.
 */
export interface HistorialPagination {
  page: number;
  setPage: (page: number | ((prev: number) => number)) => void;
  total: number;
  limit: number;
  totalPages: number;
}

/**
 * Par Before / After para comparación de conteos y ajustes.
 */
export interface BeforeAfterDelta {
  before: number;
  after: number;
}

/**
 * Respuesta del backend para `/api/v1/inventory/history/paginated`.
 */
export interface PaginatedKardexHistoryResponse {
  total: number;
  skip: number;
  limit: number;
  page: number;
  total_pages: number;
  items: RegistroMovimiento[];
}

/**
 * Opciones para inicializar el hook useHistorial.
 */
export interface UseHistorialOptions {
  selectedBodegaId?: string | number | "all";
  initialLimit?: number;
}

/**
 * Valor retornado por useHistorial.
 */
export interface UseHistorialReturn {
  registros: RegistroMovimiento[];
  filtered: RegistroMovimiento[];
  loading: boolean;
  isLoading: boolean;
  isError: boolean;
  productos: HistorialCatalogProduct[];
  filtros: HistorialFilters;
  pagination: HistorialPagination;
  computeBeforeAfter: (r: RegistroMovimiento) => BeforeAfterDelta | null;
  prodName: (id: string | number) => string;
  prodUnit: (id: string | number) => string;
  tipoLabel: (t: string) => string;
  refetch: () => Promise<unknown>;
}
