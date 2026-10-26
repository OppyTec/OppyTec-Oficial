// oppytec-frontend/src/features/consumo/types.ts
/**
 * Contratos TypeScript de Dominio para el Módulo de Registro de Consumo,
 * Manos Libres (Cocina por Voz) y Buffet Inteligente (OppyTec v2.0).
 * Conforme a PLAN_MAESTRO_CONSUMO.md Fase 1 y 3.
 */

// ============================================================================
// 1. CONSTANTES DE CONFIGURACIÓN Y CATÁLOGO
// ============================================================================

export const DEFAULT_CONSUMO_COLS = 8 as const;
export const MIN_CONSUMO_COLS = 5 as const;
export const MAX_CONSUMO_COLS = 10 as const;

export const PAGE_SIZE_OPTIONS: readonly number[] = [24, 48, 96] as const;

export type ConsumoCatalogMode = "productos" | "recetas" | "combos";

export type ConsumoSortMode =
  | "manual"
  | "alpha_asc"
  | "alpha_desc"
  | "most_consumed"
  | "category";

// ============================================================================
// 2. CATÁLOGO: CATEGORÍAS, PRODUCTOS, RECETAS Y COMBOS
// ============================================================================

export interface CategoriaConsumo {
  id: string;
  nombre: string;
  area_operativa_ids?: string[];
  color?: string;
  icono?: string;
}

export type Categoria = CategoriaConsumo;

export interface LotInfo {
  lote_codigo?: string | null;
  fecha_vencimiento: string;
  cantidad: number;
}

export type Lot = LotInfo;

export interface ProductoConsumo {
  id: string;
  nombre: string;
  unidad: string;
  categoria_id: string;
  sku?: string;
  stock_minimo?: number;
  costo_unitario?: number;
  stock_disponible?: number;
  categoria?: CategoriaConsumo;
  categorias_config?: unknown[];
  dias_alerta_vencimiento?: number;
  precio_venta?: number;
  cantidad_consumos?: number;
  imagen_url?: string | null;
  lotes?: LotInfo[];
}

export type Producto = ProductoConsumo;

export interface RecetaIngredienteConsumo {
  producto_id?: string | null;
  grupo_opciones_id?: string | null;
  cantidad: number;
  unidad?: string;
  bodega_id: string;
}

export type RecetaIngrediente = RecetaIngredienteConsumo;

export interface RecetaConsumo {
  id: string;
  nombre: string;
  precio: number;
  porciones?: number;
  imagen_url?: string | null;
  imagenes_galeria?: string[];
  ingredientes: RecetaIngredienteConsumo[];
  categoria_receta_id?: string | null;
  areas_operativas_ids?: string[] | null;
  disponibilidad_por_bodega?: Array<{
    bodega_id: string;
    bodega_nombre: string;
    cantidad: number;
  }>;
  costo_total?: number;
}

export type Receta = RecetaConsumo;

export interface OptionSelection {
  grupo_id: string;
  producto_id?: string | null;
  receta_id?: string | null;
  cantidad: number;
  nombre?: string;
  precio_adicional?: number;
}

export interface ComboItemConsumo {
  id: string;
  combo_id?: string;
  producto_id?: string | null;
  receta_id?: string | null;
  grupo_opciones_id?: string | null;
  cantidad: number;
  nombre?: string;
  type?: "producto" | "receta" | "grupo";
  precio?: number;
}

export type ComboItem = ComboItemConsumo;

export interface ComboConsumo {
  id: string;
  nombre: string;
  precio: number;
  iva_incluido?: boolean;
  iva_porcentaje?: number;
  imagen_url?: string | null;
  items: ComboItemConsumo[];
  costo_total?: number;
  precio_neto?: number;
  precio_bruto?: number;
  disponibilidad?: number;
  categoria_combo_id?: string | null;
}

export type Combo = ComboConsumo;

// ============================================================================
// 3. CARRITO DE CONSUMO Y OVERRIDES
// ============================================================================

export interface IngredientLotOverride {
  producto_id: string;
  fecha_vencimiento: string | null;
  lote_codigo?: string | null;
}

export interface CartItem {
  id: string;
  cartItemId: string;
  name: string;
  type: "producto" | "receta" | "combo";
  quantity: number;
  bodega_id: string;
  unit?: string;
  price?: number;
  // Selección manual de lote para productos individuales (null = FEFO automático)
  selectedLot?: string | null;
  // Overrides de lote por ingrediente para recetas (null fecha = FEFO automático)
  ingredientLotOverrides?: IngredientLotOverride[];
  // Selecciones de grupos de opciones para recetas y combos
  optionSelections?: OptionSelection[];
}

// ============================================================================
// 4. PLANTILLAS DE CONSUMO
// ============================================================================

export interface ConsumoTemplate {
  id: string;
  name: string;
  description?: string;
  isPublic: boolean;
  author?: string;
  createdBy?: string | number;
  productIds: string[];
  columnsCount: number; // 5 a 10
  sortMode?: ConsumoSortMode;
  customProductOrder?: string[];
  createdAt?: string;
  updatedAt?: string;
}

// ============================================================================
// 5. HISTORIAL Y REGISTROS DE CONSUMO (KARDEX AUDITABLE)
// ============================================================================

export interface ConsumptionRecordItem {
  id: string;
  consumption_record_id?: string;
  tipo_item: "producto" | "receta" | "combo" | "PRODUCTO" | "RECETA" | "COMBO";
  item_id: string;
  nombre?: string;
  cantidad: number;
  unidad_medida?: string;
  costo_unitario_ppp?: number;
  costo_total?: number;
  lote_codigo?: string | null;
  fecha_vencimiento_lote?: string | null;
  kardex_movement_id?: string | number | null;
  opciones_seleccionadas?: OptionSelection[] | null;
}

export interface ConsumptionRecord {
  id: string;
  codigo_folio?: string;
  area_operativa_id?: string;
  bodega_id: string;
  usuario_id?: number | string;
  usuario_nombre?: string;
  user_display_name?: string;
  tipo_origen?:
    | "MANUAL_TERMINAL"
    | "MANOS_LIBRES_VOZ"
    | "BUFFET_LIQUIDACION"
    | "VENTA_POS"
    | string;
  tipo_movimiento?: string;
  producto_id?: string;
  nombre_producto?: string;
  cantidad?: number;
  cantidad_anterior?: number;
  unidad_medida?: string;
  costo_unitario?: number;
  costo_total?: number;
  precio_venta?: number;
  fecha_vencimiento?: string;
  nombre_receta?: string;
  nombre_bodega?: string;
  receta_consumo_id?: string;
  receta_id?: string;
  motivo_merma?: string;
  descripcion_merma?: string;
  transfer_id?: string;
  notas?: string | null;
  items?: ConsumptionRecordItem[];
  insumos?: ConsumptionRecordItem[];
  estado?: "CONFIRMADO" | "ANULADO" | "PENDIENTE" | string;
  created_at: string;
  updated_at?: string;
}

// ============================================================================
// 6. BUFFET INTELIGENTE: SESIONES, ESTACIONES Y CONCILIACIÓN PAX
// ============================================================================

export interface BoundingBox {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
}

export interface BuffetItemDetection {
  item_id: string;
  item_type: "producto" | "receta";
  name: string;
  count: number;
  unit?: string;
  bounding_boxes: number[][]; // [[ymin, xmin, ymax, xmax], ...]
  confidence: number;
}

export interface BuffetStationScanResponse {
  station_name_suggestion: string;
  detections: BuffetItemDetection[];
  foto_original_url: string;
}

export interface BuffetItemUpdate {
  item_id: string;
  item_type: "producto" | "receta";
  nombre: string;
  cantidad: number;
  bodega_id?: string | null;
  accion_sobrante?: "retornar" | "merma";
  motivo_merma?: string | null;
  notas?: string | null;
}

export interface BodegaConflictInfo {
  tipo: "consumo_default" | "multiple_consumo" | "none";
  bodega_asignada_id: string;
  bodega_asignada_nombre: string;
  otras_bodegas?: Array<{
    id: string;
    nombre: string;
    stock_actual: number;
    es_consumo: boolean;
  }>;
  opciones_consumo?: Array<{
    id: string;
    nombre: string;
    stock_actual: number;
    es_consumo: boolean;
  }>;
  mensaje: string;
}

export interface BuffetSessionItem {
  id: string;
  item_type: "producto" | "receta";
  producto_id?: string | null;
  receta_id?: string | null;
  station_id?: string | null;
  bodega_id?: string | null;
  bodega_nombre?: string | null;
  bodegas_disponibles?: Array<{
    id: string;
    nombre: string;
    stock_actual: number;
    es_consumo: boolean;
  }>;
  bodega_conflict?: BodegaConflictInfo | null;
  nombre: string;
  unidad: string;
  cantidad_apertura: number;
  cantidad_reposiciones: number;
  cantidad_cierre: number;
  cantidad_consumida: number;
  cantidad_sobrante: number;
  accion_sobrante: "retornar" | "merma";
  motivo_merma?: string | null;
  costo_unitario_ppp?: number;
  costo_total?: number;
  imagen_url?: string | null;
  estacion_nombre?: string;
}

export interface BuffetStation {
  id: string;
  buffet_session_id?: string;
  nombre_estacion: string;
  fase?: "apertura" | "reposicion" | "cierre";
  foto_original_url?: string;
  foto_anotada_url?: string | null;
  detecciones_json?: BuffetItemDetection[] | unknown[];
  orden: number;
  created_at?: string;
}

export interface BuffetSession {
  id: string;
  nombre?: string;
  tipo_servicio?: "DESAYUNO" | "ALMUERZO" | "BRUNCH" | "EVENTO" | string;
  bodega_id?: string | null;
  bodega_nombre?: string | null;
  bodegas_ids?: string[];
  bodegas_nombres?: string[];
  area_operativa_id?: string | null;
  area_operativa_nombre?: string | null;
  usuario_creador_id: number;
  usuario_creador_nombre?: string | null;
  estado:
    | "apertura"
    | "abierto"
    | "cierre"
    | "pendiente_aprobacion"
    | "aprobado"
    | "rechazado"
    | "EN_PREPARACION"
    | "ACTIVO"
    | "CERRADO"
    | "CONCILIADO"
    | string;
  solicitud_aprobacion_id?: string | null;
  pax_comensales?: number;
  costo_total_montaje?: number;
  valor_sobrante_reutilizable?: number;
  costo_neto_pax?: number;
  fecha_apertura?: string | null;
  fecha_cierre?: string | null;
  notas?: string | null;
  created_at: string;
  updated_at: string;
  estaciones: BuffetStation[];
  items: BuffetSessionItem[];
}

export interface BuffetStationTemplateItem {
  nombre_estacion: string;
  orden: number;
  items_predeterminados?: Array<{
    item_type: "producto" | "receta";
    item_id: string;
    cantidad_estandar: number;
  }>;
}

export interface BuffetTemplate {
  id: string;
  nombre: string;
  descripcion?: string | null;
  bodega_id?: string | null;
  bodega_nombre?: string | null;
  bodegas_ids?: string[];
  bodegas_nombres?: string[];
  area_operativa_id?: string | null;
  area_operativa_nombre?: string | null;
  comensales_estimados?: number | null;
  estaciones: string[] | BuffetStationTemplateItem[];
  items?: BuffetSessionItem[] | unknown[];
  isPublic: boolean;
  createdBy?: number;
  createdByName?: string | null;
  isSystem?: boolean;
  created_at?: string;
  updated_at?: string;
}

// ============================================================================
// 7. COCINA POR VOZ / MANOS LIBRES
// ============================================================================

export interface WorkerStation {
  id: number;
  name: string;
  username: string;
  voice_command: string;
  role: string;
  user_image?: string | null;
  area_operativa_id?: string | number | null;
  active?: boolean;
}

export interface VoiceOrderItem {
  id?: string | null;
  name: string;
  quantity: number;
  unit: string;
  motivo_merma?: string | null;
}

export interface VoiceOrderLog {
  solicitud_id: string;
  timestamp: Date | string;
  worker: {
    id: number;
    name: string;
    voice_command?: string;
  };
  action_type: "consumo" | "merma";
  item: {
    name: string;
    quantity: number;
    unit: string;
  };
  items?: VoiceOrderItem[];
  motivo_merma?: string | null;
  impacto_costo?: number;
  impacto_venta?: number;
  spoken_feedback: string;
  transcript: string;
  confidence?: number;
  status?: "PENDIENTE" | "CONFIRMADO" | "RECHAZADO" | "EJECUTADO" | string;
  consumption_record_id?: string | null;
}
