/**
 * oppytec-frontend/src/features/procurement/types.ts
 * Contratos TypeScript de Dominio para Abastecimiento, Compras, Proveedores y Analítica de Mermas.
 * Precisión Decimal estricta (cero floats) y compatibilidad con schemas Pydantic v2.
 */

// ============================================================================
// PROVEEDORES Y CATÁLOGO PACTADO
// ============================================================================

export type ProveedorEstado = "ACTIVO" | "INACTIVO";

export interface Proveedor {
  id: number;
  rut_tax_id: string;
  razon_social: string;
  nombre_fantasia: string | null;
  email_contacto: string | null;
  telefono: string | null;
  direccion: string | null;
  lead_time_dias: number;
  estado: ProveedorEstado;
  notas: string | null;
  created_at: string | null;
  updated_at: string | null;
  total_compras_historicas?: string | number;
  ordenes_activas_count?: number;
}

export interface ProductoProveedor {
  id: number | null;
  producto_id: number;
  producto_nombre: string | null;
  producto_sku?: string | null;
  proveedor_id: number;
  codigo_proveedor?: string | null;
  codigo_producto_proveedor?: string | null;
  ultimo_costo_neto?: string | number;
  precio_pactado?: string | number;
  tiempo_entrega_dias: number | null;
  es_proveedor_principal: boolean;
}

// ============================================================================
// ÓRDENES DE COMPRA Y DETALLES
// ============================================================================

export type CompraEstado =
  | "BORRADOR"
  | "SOLICITADA"
  | "EN_CAMINO"
  | "RECIBIDA_PARCIAL"
  | "RECIBIDA_TOTAL"
  | "CANCELADA";

export interface CompraItem {
  id: number | null;
  compra_id: number | null;
  producto_id: number;
  producto_nombre: string | null;
  producto_sku?: string | null;
  cantidad_solicitada: string | number;
  cantidad_recibida: string | number;
  costo_unitario_neto: string | number;
  subtotal_linea: string | number;
  lote_codigo: string | null;
  fecha_vencimiento: string | null;
}

export interface CompraIncidencia {
  id: number;
  compra_id: number;
  compra_item_id: number | null;
  tipo_incidencia: string;
  cantidad_afectada: string | number;
  monto_disputa: string | number;
  resolucion: string;
  descripcion: string;
  foto_evidencia_url: string | null;
  created_at: string | null;
  registrado_por_user_id?: number | null;
}

export interface CompraOrder {
  id: number | null;
  numero_orden: string;
  po_number?: string;
  proveedor_id: number;
  proveedor_nombre: string;
  supplier_id?: number;
  supplier_name?: string;
  bodega_destino_id: number;
  bodega_nombre: string | null;
  estado: CompraEstado;
  moneda: string;
  tasa_fx_aplicada: string | number;
  monto_neto: string | number;
  monto_impuestos: string | number;
  monto_total: string | number;
  fecha_emision: string | null;
  fecha_entrega_comprometida: string | null;
  fecha_entrega_estimada?: string | null;
  fecha_recepcion_real: string | null;
  notas: string | null;
  items_count: number;
  items: CompraItem[];
  incidencias?: CompraIncidencia[];
}

// ============================================================================
// DASHBOARD Y MÉTRICAS DE PROCUREMENT
// ============================================================================

export interface GastoProveedorItem {
  proveedor_id?: number;
  razon_social?: string;
  total?: string | number;
  total_costo?: string | number;
  porcentaje?: string | number;
}

export interface ProcurementDashboardData {
  monto_total_mes: string | number;
  total_mes_monto?: string | number;
  ordenes_pendientes: number;
  ordenes_pendientes_recepcion?: number;
  proveedores_activos: number;
  proveedor_principal: string | null;
  tiempo_promedio_entrega_dias: number;
  variacion_mes_anterior_pct: string | number;
  ordenes_recientes?: CompraOrder[];
  gastos_por_proveedor?: GastoProveedorItem[];
}

// ============================================================================
// ANALÍTICA Y GESTIÓN DE MERMAS
// ============================================================================

export interface MermaByMotivo {
  motivo: string;
  total_costo: string | number;
  cantidad: string | number;
  porcentaje: string | number;
}

export interface MermaByCategoria {
  categoria_id: number;
  categoria_nombre: string;
  total_costo: string | number;
  cantidad: string | number;
}

export interface MermaTimelinePoint {
  fecha: string;
  costo: string | number;
  cantidad: string | number;
}

export interface MermaHistoryItem {
  id: number;
  producto_id: number;
  producto_nombre: string | null;
  producto_sku?: string | null;
  bodega_id: number;
  bodega_nombre?: string | null;
  cantidad: string | number;
  costo_total: string | number;
  motivo: string;
  estado_aprobacion: string;
  reportado_por_user_id: number;
  fecha_merma?: string | null;
  created_at?: string | null;
}

export interface MermaAnalyticsData {
  total_perdida_ppp: string | number;
  unidades_mermadas: string | number;
  items_mermados_count?: number;
  mermas_pendientes_aprobacion?: number;
  ratio_merma_ventas: string | number;
  motivo_principal: string;
  motivos_breakdown: MermaByMotivo[];
  por_motivo?: MermaByMotivo[];
  por_categoria?: MermaByCategoria[];
  timeline: MermaTimelinePoint[];
  history_items?: MermaHistoryItem[];
}

export type DateRangePreset =
  | "hoy"
  | "7d"
  | "30d"
  | "mes_actual"
  | "mes_anterior"
  | "personalizado";

export interface DateRangeFilter {
  preset: DateRangePreset;
  date_from: string | null;
  date_to: string | null;
}

// ============================================================================
// PAYLOADS DE MUTACIONES
// ============================================================================

export interface CreateProveedorPayload {
  rut_tax_id: string;
  razon_social: string;
  nombre_fantasia?: string | null;
  email_contacto?: string | null;
  telefono?: string | null;
  direccion?: string | null;
  lead_time_dias?: number;
  estado?: ProveedorEstado;
  notas?: string | null;
}

export interface UpdateProveedorPayload {
  razon_social?: string;
  nombre_fantasia?: string | null;
  email_contacto?: string | null;
  telefono?: string | null;
  direccion?: string | null;
  lead_time_dias?: number;
  estado?: ProveedorEstado;
  notas?: string | null;
}

export interface SupplierCatalogItemPayload {
  producto_id: number;
  precio_pactado: string | number;
  codigo_producto_proveedor?: string | null;
  tiempo_entrega_dias?: number | null;
  es_proveedor_principal?: boolean;
}

export interface UpdateSupplierCatalogPayload {
  supplier_id: number;
  items: SupplierCatalogItemPayload[];
}

export interface OrderItemInput {
  producto_id: number;
  cantidad_solicitada: number;
  costo_unitario_neto: number;
  lote_codigo?: string | null;
  fecha_vencimiento?: string | null;
}

export interface CreateOrderPayload {
  numero_orden?: string;
  po_number?: string;
  proveedor_id: number;
  proveedor_nombre?: string;
  supplier_id?: number;
  supplier_name?: string;
  bodega_destino_id?: number;
  moneda?: string;
  fecha_entrega_comprometida?: string | null;
  fecha_entrega_estimada?: string | null;
  notas?: string | null;
  items: OrderItemInput[];
}

export interface ReceiveGoodsItemPayload {
  compra_item_id?: number | null;
  producto_id: number;
  cantidad_recibida: number;
  costo_unitario_neto?: number | null;
  lote_codigo?: string | null;
  fecha_vencimiento?: string | null;
}

export interface ReceiveGoodsPayload {
  order_id: number;
  items: ReceiveGoodsItemPayload[];
  notas?: string | null;
}

export interface RegisterIncidencePayload {
  order_id: number;
  compra_item_id?: number | null;
  tipo_incidencia: string;
  cantidad_afectada: number;
  monto_disputa?: number;
  resolucion?: string;
  descripcion: string;
  foto_evidencia_url?: string | null;
}

export interface CancelOrderPayload {
  order_id: number;
  motivo: string;
}

// ============================================================================
// BORRADOR LOCALSTORAGE (AUTO-RECUPERACIÓN RESILIENTE)
// ============================================================================

export const COMPRA_DRAFT_STORAGE_KEY = "oppytec_compra_draft";

export interface CompraDraftItem {
  producto_id: number;
  producto_nombre: string;
  cantidad_solicitada: number;
  costo_unitario_neto: number;
  subtotal_linea: number;
  lote_codigo?: string | null;
  fecha_vencimiento?: string | null;
}

export interface CompraDraft {
  proveedor_id: number | null;
  proveedor_nombre?: string;
  bodega_destino_id: number;
  bodega_nombre?: string;
  fecha_entrega_comprometida?: string | null;
  moneda: string;
  notas: string;
  items: CompraDraftItem[];
  updated_at: string;
}
