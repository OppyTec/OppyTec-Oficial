// oppytec-frontend/src/features/inventory/types.ts
/**
 * Contratos TypeScript de Dominio para el Módulo de Inventario Multi-Bodega,
 * Kardex Inmutable y Auditorías Físicas (OppyTec v2.0).
 */

export interface StorageLocation {
  pasillo?: string | null;
  estante?: string | null;
  nivel?: string | null;
  coordenada_letra?: string | null;
  coordenada_numero?: string | null;
}

export type MovementType =
  | "ENTRADA"
  | "SALIDA"
  | "COMPRA"
  | "CONSUMO"
  | "MERMA"
  | "TRASPASO_IN"
  | "TRASPASO_OUT"
  | "AJUSTE_POSITIVO"
  | "AJUSTE_NEGATIVO"
  | "AJUSTE_AUDITORIA"
  | "entrada"
  | "salida"
  | "compra"
  | "consumo"
  | "merma"
  | "transferencia"
  | "ajuste_positivo"
  | "ajuste_negativo"
  | "ajuste_auditoria";

export type StockSemaforo = "CRITICO" | "MINIMO" | "OPTIMO";

export type StockSeverityLevel =
  | "vencido"
  | "vence_hoy"
  | "proximo"
  | "vigente"
  | "sin_fecha"
  | "no_perecible";

export interface InventoryLot {
  lote_codigo: string;
  fecha_vencimiento: string;
  cantidad: number;
}

export interface StockItem {
  id: number | string;
  producto_id: number;
  nombre: string;
  sku: string;
  categoria: string;
  categoria_color?: string;
  categoria_icono?: string;
  bodega_id: number;
  bodega_nombre: string;
  stock_actual: number;
  stock_minimo: number;
  stock_maximo?: number | null;
  punto_reorden?: number | null;
  unidad_medida: string;
  ubicacion: StorageLocation;
  costo_unitario_ppp: number;
  costo_total_valorizado: number;
  semaforo: StockSemaforo;
  lotes: InventoryLot[];
  dias_alerta_vencimiento?: number;
  no_perecible?: boolean;
}

export interface StockMovement {
  id: number;
  created_at: string;
  producto_id: number;
  producto_nombre: string;
  bodega_id: number;
  bodega_nombre: string;
  tipo_movimiento: MovementType;
  cantidad: number;
  saldo_resultante: number;
  costo_unitario: number;
  actor_nombre: string;
  documento_referencia?: string | null;
  transfer_id?: string | null;
  lote_codigo?: string | null;
  fecha_vencimiento_lote?: string | null;
}

export interface PhysicalCountItem {
  id?: number;
  conteo_id?: number;
  producto_id: number;
  producto_nombre: string;
  unidad_medida: string;
  lote_codigo?: string | null;
  fecha_vencimiento?: string | null;
  stock_teorico_sistema: number;
  stock_fisico_contado: number;
  diferencia_unidades: number;
  costo_unitario_ppp: number;
  valorizacion_diferencia: number;
  has_discrepancy?: boolean;
  is_surplus?: boolean;
  is_shortage?: boolean;
}

export type PhysicalCountState =
  | "EN_PROGRESO"
  | "PENDIENTE_APROBACION"
  | "APROBADO"
  | "RECHAZADO"
  | "ANULADO";

export interface PhysicalCountSession {
  id: number;
  bodega_id: number;
  bodega_nombre: string;
  area_operativa_id?: number | null;
  estado: PhysicalCountState;
  responsable_user_id?: number;
  responsable_nombre: string;
  aprobador_user_id?: number | null;
  aprobador_nombre?: string | null;
  fecha_inicio: string;
  fecha_cierre?: string | null;
  total_items_contados: number;
  total_discrepancias_unidades: number;
  total_valorizacion_discrepancia: number;
  items: PhysicalCountItem[];
  notas?: string | null;
}

export interface StockTransfer {
  id: number;
  transfer_uuid: string;
  bodega_origen_id: number;
  bodega_origen_nombre?: string;
  bodega_destino_id: number;
  bodega_destino_nombre?: string;
  estado: "SOLICITADA" | "EN_TRANSITO" | "COMPLETADA" | "CANCELADA";
  items: Array<{
    producto_id: number;
    cantidad: number;
    producto_nombre?: string;
  }>;
  fecha_transferencia?: string | null;
}

export interface MermaItem {
  id: number;
  producto_id: number;
  producto_nombre: string;
  bodega_id: number;
  bodega_nombre?: string;
  cantidad: number;
  costo_total: number;
  unit_cost?: number;
  motivo: string;
  estado: "PENDIENTE" | "APROBADA" | "RECHAZADA";
  reporter_user_id?: number;
  created_at?: string;
}

// ----------------------------------------------------------------------------
// Columnas y Filtros de Tabla
// ----------------------------------------------------------------------------

export interface StockColumnDef {
  readonly id: string;
  readonly label: string;
  readonly width: string;
  readonly minWidthPx: number;
}

export const STOCK_COLUMNS: readonly StockColumnDef[] = [
  { id: "semaforo", label: "Estado / Alerta", width: "w-[130px]", minWidthPx: 130 },
  { id: "producto", label: "Producto", width: "w-[240px]", minWidthPx: 240 },
  { id: "sku", label: "SKU", width: "w-[120px]", minWidthPx: 120 },
  { id: "categoria", label: "Categoría", width: "w-[140px]", minWidthPx: 140 },
  { id: "bodega", label: "Bodega", width: "w-[150px]", minWidthPx: 150 },
  { id: "ubicacion", label: "Ubicación", width: "w-[120px]", minWidthPx: 120 },
  { id: "stock_actual", label: "Stock Actual", width: "w-[140px]", minWidthPx: 140 },
  { id: "lotes", label: "Lotes & FEFO", width: "w-[180px]", minWidthPx: 180 },
  { id: "costo_unitario_ppp", label: "Costo PPP", width: "w-[130px]", minWidthPx: 130 },
  { id: "costo_total_valorizado", label: "Valor Total", width: "w-[140px]", minWidthPx: 140 },
  { id: "acciones", label: "Acciones", width: "w-[120px]", minWidthPx: 120 },
] as const;

export type StockViewMode = "agrupado" | "plano";

export type StockSortOption = "urgency" | "az" | "za" | "stock_asc" | "stock_desc";

export interface StockFilter {
  search: string;
  bodega_id?: number | "all";
  area_operativa_id?: number | "all";
  semaforo?: "ALL" | StockSemaforo;
  categoria?: string;
  sortBy?: StockSortOption;
}

// ----------------------------------------------------------------------------
// Compatibilidad con Formatos de Conteo Ciego y Legacy
// ----------------------------------------------------------------------------

export type ConteoStep = "idle" | "counting" | "reviewing" | "submitting" | "finished";

export interface ConteoItemDraft {
  localId: string;
  producto_id: number;
  producto_nombre?: string;
  unidad_medida?: string;
  stock_fisico_contado: number;
  lote_codigo?: string | null;
  fecha_vencimiento?: string | null;
  costo_unitario_ppp?: number;
}

export type ConteoItem = ConteoItemDraft;
export type ConteoSession = PhysicalCountSession;
export type DiscrepanciaActaItem = PhysicalCountItem;

export interface ExpiryEntry {
  fecha_vencimiento: string;
  cantidad: number;
  lote_codigo?: string;
  dias_vencimiento?: number | null;
  vigencia_texto?: string;
  estado_vigencia?: StockSeverityLevel;
}

export interface StockEntry {
  cantidad: number;
  fecha_recuento?: string;
  fecha_vencimiento?: string;
  multiExpiry?: boolean;
  expiryEntries: ExpiryEntry[];
}

export interface DisplayStockProduct extends StockItem {
  _entryKey?: string;
}

// ----------------------------------------------------------------------------
// Payloads de Operación
// ----------------------------------------------------------------------------

export interface BulkTransferItemPayload {
  producto_id: number;
  cantidad: number;
  producto_nombre?: string;
}

export interface BulkTransferPayload {
  bodega_origen_id: number;
  bodega_destino_id: number;
  items: BulkTransferItemPayload[];
  fecha_transferencia?: string | null;
}

export interface MovementPayload {
  producto_id: number;
  bodega_id: number;
  cantidad: number;
  tipo_movimiento: MovementType;
  unit_cost?: number;
  lote_codigo?: string | null;
  fecha_vencimiento_lote?: string | null;
  documento_referencia?: string | null;
}

export interface AdjustmentPayload {
  producto_id: number;
  bodega_id: number;
  tipo_movimiento: "AJUSTE_POSITIVO" | "AJUSTE_NEGATIVO";
  cantidad: number;
  unit_cost: number;
  reason: string;
  lote_codigo?: string | null;
  fecha_vencimiento_lote?: string | null;
}

export interface MermaPayload {
  producto_id: number;
  bodega_id: number;
  quantity: number;
  unit_cost: number;
  reason: string;
  lote_codigo?: string | null;
}
