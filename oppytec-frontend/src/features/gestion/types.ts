// oppytec-frontend/src/features/gestion/types.ts

export interface EtiquetaProducto {
  id: string;
  nombre: string;
  color?: string | null;
  icono?: string | null;
}

export interface Marca {
  id: string;
  nombre: string;
  logo_url?: string | null;
}

export interface TipoEnvase {
  id: string;
  nombre: string;
  icono?: string | null;
  es_predeterminado?: boolean;
}

export interface FamiliaProducto {
  id: string;
  nombre: string;
}

export interface Categoria {
  id: string;
  nombre: string;
  color?: string;
  icono?: string;
  tipo_categoria?: string | null;
  area_operativa_ids?: string[];
}

export interface CategoriaReceta {
  id: string;
  nombre: string;
  color?: string;
  icono?: string;
}

export interface BodegaConfig {
  bodega_id: string;
  stock_minimo: number;
  stock_actual?: number;
  coordenada_letra?: string | null;
  coordenada_numero?: string | null;
  bodega_nombre?: string;
}

export interface ProductoBodega {
  producto_id: string;
  bodega_id: string;
  stock_minimo: number;
  coordenada_letra?: string | null;
  coordenada_numero?: string | null;
  bodega_nombre?: string;
}

export interface PresentacionCompra {
  nombre: string;
  equivalencia: number;
  proveedor_id?: string | null;
  ultimo_costo?: number;
  penultimo_costo?: number;
  costo_bruto?: number;
  iva_porcentaje?: number;
  tipo_embalaje?: string;
  tipo_envase_id?: string | null;
  formato_envase_id?: string | null;
  contenido_envase?: number | null;
  cantidad?: number;
  unidad_medida?: string;
  sku?: string;
  codigo_barra?: string;
  imagen_url?: string | null;
  proveedores_costos?: {
    id?: string;
    proveedor_id?: string | null;
    ultimo_costo?: number | null;
    costo_bruto?: number | null;
    iva_porcentaje?: number | null;
  }[];
}

export interface ProveedorVinculado {
  proveedor_id: string;
  ultimo_costo?: number | null;
  presentaciones_proveedor?: {
    nombre: string;
    equivalencia: number;
    proveedor_id?: string;
    ultimo_costo?: number;
  }[];
  alias_factura?: string[];
}

export interface Producto {
  id: string;
  nombre: string;
  nombre_completo?: string | null;
  categoria_id: string;
  familia_id?: string | null;
  marca_id?: string | null;
  tipo_envase_id?: string | null;
  etiquetas_ids?: string[];
  etiquetas?: EtiquetaProducto[];
  estado?: "activo" | "borrador_incompleto" | "archivado" | string;

  unidad: string;
  costo_unitario: number;
  iva_incluido?: boolean;
  iva_porcentaje?: number;
  imagen_url?: string | null;
  imagenes_galeria?: { id: string; url: string; is_primary?: boolean }[] | null;
  precio_venta?: number | null;
  codigo_barra?: string | null;
  factor_conversion?: number | null;
  unidad_conversion?: string | null;
  marca?: string | null;
  proveedor?: string | null;
  proveedor_id?: string | null;
  proveedores_vinculados?: ProveedorVinculado[];
  proveedores_config?: ProveedorVinculado[];
  areas_operativas_ids?: string[];
  sku?: string | null;
  dias_alerta_vencimiento?: number;
  no_perecible?: boolean;
  presentaciones_compra?: PresentacionCompra[];

  // Relaciones cargadas
  familia?: FamiliaProducto | null;
  marca_rel?: Marca | null;
  tipo_envase_rel?: TipoEnvase | null;

  // 3 capas y métricas de costos
  unidad_envase?: string | null;
  contenido_envase?: number | null;
  contenido_drenado?: number | null;
  costo_unitario_ultimo?: number | null;
  costo_unitario_penultimo?: number | null;
  costo_unitario_promedio_10?: number | null;
  costo_unitario_ppp?: number | null;
  costo_penultimo?: number | null;
  penultimo_costo?: number | null;
  costo_promedio_inventario?: number | null;
  costo_promedio_historico?: number | null;
  valor_inventario?: number | null;
  unidades_vendidas_mes?: number | null;
  consumo_diario_promedio?: number | null;

  bodegas_config: BodegaConfig[];
  stock_actual?: number;
  proxima_expiracion?: string | null;
  costo_promedio?: number;
  ultimo_costo?: number;
}

export interface IngredienteReceta {
  id?: string;
  producto_id?: string | null;
  grupo_opciones_id?: string | null;
  bodega_id?: string;
  cantidad: number;
  nombre_producto?: string;
  nombre_grupo?: string;
  unidad?: string;
  type?: "producto" | "grupo";
}

export interface Receta {
  id: string;
  nombre: string;
  precio: number;
  porciones?: number;
  iva_incluido?: boolean;
  iva_porcentaje?: number;
  imagen_url?: string | null;
  imagenes_galeria?: { id: string; url: string; is_primary?: boolean }[] | null;
  categoria_receta_id?: string | null;
  areas_operativas_ids?: string[];
  ingredientes: IngredienteReceta[];
  costo_total?: number;
  costo_porcion?: number;
  precio_neto?: number;
  precio_bruto?: number;

  // Preparación y multimedia
  preparacion?: string | null;
  video_url?: string | null;
  documento_url?: string | null;

  // Métricas dinámicas de Gestión
  disponibilidad_por_bodega?: { bodega_id: string; bodega_nombre: string; cantidad: number }[];
  consumo_diario?: number;
  consumo_semanal?: number;
  consumo_mensual?: number;
}

export interface ComboItem {
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

export interface CategoriaCombo {
  id: string;
  nombre: string;
  color?: string;
  icono?: string;
}

export interface Combo {
  id: string;
  nombre: string;
  precio: number;
  iva_incluido?: boolean;
  iva_porcentaje?: number;
  imagen_url?: string | null;
  items: ComboItem[];
  costo_total?: number;
  precio_neto?: number;
  precio_bruto?: number;
  disponibilidad?: number;
  categoria_combo_id?: string | null;
}

export interface GrupoOpcionesItem {
  id?: string;
  grupo_id?: string;
  producto_id?: string | null;
  receta_id?: string | null;
  precio_adicional: number;
  iva_incluido: boolean;
  iva_porcentaje: number;
  nombre?: string;
  type?: "producto" | "receta";
}

export interface GrupoOpciones {
  id: string;
  nombre: string;
  seleccion_minima: number;
  seleccion_maxima: number;
  items: GrupoOpcionesItem[];
  created_at?: string;
}

export type ViewTab =
  | "productos"
  | "recetas"
  | "combos"
  | "grupos-opciones"
  | "pedidos"
  | "compras"
  | "mermas";

export type ViewMode = "agrupado" | "simple";

export interface SortOption<TSortKey extends string = string> {
  label: string;
  key: TSortKey;
  direction: "asc" | "desc";
}

export interface ColumnOption<TColKey extends string = string> {
  key: TColKey;
  label: string;
  section?: string;
  subsection?: string;
  counterpartKey?: TColKey;
  isNeto?: boolean;
  isBruto?: boolean;
}

export interface TablePreset<TColKey extends string = string, TSortKey extends string = string> {
  id: string;
  name: string;
  description?: string;
  columns: TColKey[];
  sortConfig?: { key: TSortKey; direction: "asc" | "desc" };
  viewMode?: ViewMode;
  isSystem?: boolean;
  isPublic?: boolean;
}

// ---------------------------------------------------------
// Columnas analíticas completas para Gestión de Productos
// Clasificadas en:
// 1. Stock y Logística
// 2. Costos de Compra
// 3. Ventas y Márgenes / Ventas y Valorización
// 4. Rotación y Autonomía
// ---------------------------------------------------------
export const ALL_COLUMNS = [
  // 📦 1. Stock y Logística
  { key: "bodega", label: "Bodega", section: "📦 Stock y Logística", subsection: "Ubicación Física" },
  { key: "ubicacion", label: "Ubicación (Pasillo/Estante)", section: "📦 Stock y Logística", subsection: "Ubicación Física" },
  { key: "stock_actual", label: "Stock Actual (Envases)", section: "📦 Stock y Logística", subsection: "Nivel de Stock" },
  { key: "stock_min", label: "Stock Mínimo (Envases)", section: "📦 Stock y Logística", subsection: "Nivel de Stock" },
  { key: "contenido_total", label: "Contenido Total (Equiv)", section: "📦 Stock y Logística", subsection: "Nivel de Stock" },

  // 💰 2. Costos de Compra - Último Costo de Adquisición
  { key: "ultimo_costo_unidad_neto", label: "Último Costo Unitario Neto", section: "💰 Costos de Compra", subsection: "Último Costo de Adquisición", isNeto: true, counterpartKey: "ultimo_costo_unidad_bruto" },
  { key: "ultimo_costo_unidad_bruto", label: "Último Costo Unitario Bruto", section: "💰 Costos de Compra", subsection: "Último Costo de Adquisición", isBruto: true, counterpartKey: "ultimo_costo_unidad_neto" },
  { key: "ultimo_costo_embalaje_neto", label: "Último Costo Embalaje Neto", section: "💰 Costos de Compra", subsection: "Último Costo de Adquisición", isNeto: true, counterpartKey: "ultimo_costo_embalaje_bruto" },
  { key: "ultimo_costo_embalaje_bruto", label: "Último Costo Embalaje Bruto", section: "💰 Costos de Compra", subsection: "Último Costo de Adquisición", isBruto: true, counterpartKey: "ultimo_costo_embalaje_neto" },

  // 💰 2. Costos de Compra - Histórico & Inflación
  { key: "penultimo_costo_unidad_neto", label: "Penúltimo Costo Unitario Neto", section: "💰 Costos de Compra", subsection: "Histórico & Inflación", isNeto: true, counterpartKey: "penultimo_costo_unidad_bruto" },
  { key: "penultimo_costo_unidad_bruto", label: "Penúltimo Costo Unitario Bruto", section: "💰 Costos de Compra", subsection: "Histórico & Inflación", isBruto: true, counterpartKey: "penultimo_costo_unidad_neto" },
  { key: "penultimo_costo_embalaje_neto", label: "Penúltimo Costo Embalaje Neto", section: "💰 Costos de Compra", subsection: "Histórico & Inflación", isNeto: true, counterpartKey: "penultimo_costo_embalaje_bruto" },
  { key: "penultimo_costo_embalaje_bruto", label: "Penúltimo Costo Embalaje Bruto", section: "💰 Costos de Compra", subsection: "Histórico & Inflación", isBruto: true, counterpartKey: "penultimo_costo_embalaje_neto" },
  { key: "variacion_costo", label: "Variación Inflacionaria (%)", section: "💰 Costos de Compra", subsection: "Histórico & Inflación" },

  // 💰 2. Costos de Compra - Valorización de Inventario (PPP)
  { key: "costo_prom_inv_unidad_neto", label: "Costo PPP Unitario Neto", section: "💰 Costos de Compra", subsection: "Valorización de Inventario (PPP)", isNeto: true, counterpartKey: "costo_prom_inv_unidad_bruto" },
  { key: "costo_prom_inv_unidad_bruto", label: "Costo PPP Unitario Bruto", section: "💰 Costos de Compra", subsection: "Valorización de Inventario (PPP)", isBruto: true, counterpartKey: "costo_prom_inv_unidad_neto" },
  { key: "costo_prom_inv_embalaje_neto", label: "Costo PPP Embalaje Neto", section: "💰 Costos de Compra", subsection: "Valorización de Inventario (PPP)", isNeto: true, counterpartKey: "costo_prom_inv_embalaje_bruto" },
  { key: "costo_prom_inv_embalaje_bruto", label: "Costo PPP Embalaje Bruto", section: "💰 Costos de Compra", subsection: "Valorización de Inventario (PPP)", isBruto: true, counterpartKey: "costo_prom_inv_embalaje_neto" },

  // 💰 2. Costos de Compra - Costo Promedio Histórico (10 compras)
  { key: "costo_prom_hist_unidad_neto", label: "Costo Prom. Hist. Unitario Neto", section: "💰 Costos de Compra", subsection: "Costo Promedio Histórico (10 compras)", isNeto: true, counterpartKey: "costo_prom_hist_unidad_bruto" },
  { key: "costo_prom_hist_unidad_bruto", label: "Costo Prom. Hist. Unitario Bruto", section: "💰 Costos de Compra", subsection: "Costo Promedio Histórico (10 compras)", isBruto: true, counterpartKey: "costo_prom_hist_unidad_neto" },
  { key: "costo_prom_hist_embalaje_neto", label: "Costo Prom. Hist. Embalaje Neto", section: "💰 Costos de Compra", subsection: "Costo Promedio Histórico (10 compras)", isNeto: true, counterpartKey: "costo_prom_hist_embalaje_bruto" },
  { key: "costo_prom_hist_embalaje_bruto", label: "Costo Prom. Hist. Embalaje Bruto", section: "💰 Costos de Compra", subsection: "Costo Promedio Histórico (10 compras)", isBruto: true, counterpartKey: "costo_prom_hist_embalaje_neto" },

  // 🏷️ 3. Ventas y Valorización
  { key: "precio_venta_neto", label: "Precio Venta Unitario Neto", section: "🏷️ Ventas y Valorización", subsection: "Precios de Venta", isNeto: true, counterpartKey: "precio_venta_bruto" },
  { key: "precio_venta_bruto", label: "Precio Venta Unitario Bruto", section: "🏷️ Ventas y Valorización", subsection: "Precios de Venta", isBruto: true, counterpartKey: "precio_venta_neto" },
  { key: "margen_bruto", label: "Margen Bruto (%)", section: "🏷️ Ventas y Valorización", subsection: "Márgenes de Ganancia", isBruto: true, counterpartKey: "margen_neto" },
  { key: "margen_neto", label: "Margen Neto (%)", section: "🏷️ Ventas y Valorización", subsection: "Márgenes de Ganancia", isNeto: true, counterpartKey: "margen_bruto" },
  { key: "valor_inventario_neto", label: "Valor Inventario Neto", section: "🏷️ Ventas y Valorización", subsection: "Valor del Inventario", isNeto: true, counterpartKey: "valor_inventario_bruto" },
  { key: "valor_inventario_bruto", label: "Valor Inventario Bruto", section: "🏷️ Ventas y Valorización", subsection: "Valor del Inventario", isBruto: true, counterpartKey: "valor_inventario_neto" },

  // ⏳ 4. Rotación y Autonomía
  { key: "dias_cobertura", label: "Días de Cobertura", section: "⏳ Rotación y Autonomía", subsection: "Movimiento de Insumos" },
  { key: "indice_rotacion", label: "Índice de Rotación (Mensual)", section: "⏳ Rotación y Autonomía", subsection: "Movimiento de Insumos" },
] as const;

export type ColumnKey = (typeof ALL_COLUMNS)[number]["key"];

export const COLUMN_WIDTHS: Record<ColumnKey, string> = {
  bodega: "w-[120px]",
  stock_actual: "w-[115px]",
  stock_min: "w-[115px]",
  contenido_total: "w-[130px]",
  ubicacion: "w-[100px]",
  ultimo_costo_unidad_neto: "w-[160px]",
  ultimo_costo_unidad_bruto: "w-[160px]",
  ultimo_costo_embalaje_neto: "w-[165px]",
  ultimo_costo_embalaje_bruto: "w-[165px]",
  penultimo_costo_unidad_neto: "w-[165px]",
  penultimo_costo_unidad_bruto: "w-[165px]",
  penultimo_costo_embalaje_neto: "w-[170px]",
  penultimo_costo_embalaje_bruto: "w-[170px]",
  variacion_costo: "w-[145px]",
  precio_venta_neto: "w-[150px]",
  precio_venta_bruto: "w-[150px]",
  margen_bruto: "w-[145px]",
  margen_neto: "w-[145px]",
  valor_inventario_neto: "w-[150px]",
  valor_inventario_bruto: "w-[150px]",
  dias_cobertura: "w-[135px]",
  indice_rotacion: "w-[155px]",
  costo_prom_inv_unidad_neto: "w-[175px]",
  costo_prom_inv_unidad_bruto: "w-[175px]",
  costo_prom_inv_embalaje_neto: "w-[180px]",
  costo_prom_inv_embalaje_bruto: "w-[180px]",
  costo_prom_hist_unidad_neto: "w-[175px]",
  costo_prom_hist_unidad_bruto: "w-[175px]",
  costo_prom_hist_embalaje_neto: "w-[180px]",
  costo_prom_hist_embalaje_bruto: "w-[180px]",
};

export const getColWidthPx = (key: string): number => {
  const str = COLUMN_WIDTHS[key as ColumnKey];
  if (!str) return 120;
  const match = str.match(/\[(\d+)px\]/);
  return match?.[1] ? parseInt(match[1], 10) : 120;
};

export const DEFAULT_COLUMNS: ColumnKey[] = [
  "ultimo_costo_unidad_neto",
  "ultimo_costo_embalaje_neto",
  "precio_venta_bruto",
  "margen_bruto",
  "valor_inventario_neto",
  "dias_cobertura",
];

export const PRODUCT_SORT_OPTIONS: SortOption<"nombre" | "stock" | "precio" | "vigencia">[] = [
  { label: "Nombre A-Z", key: "nombre", direction: "asc" },
  { label: "Nombre Z-A", key: "nombre", direction: "desc" },
  { label: "Stock: Menor a Mayor", key: "stock", direction: "asc" },
  { label: "Stock: Mayor a Menor", key: "stock", direction: "desc" },
  { label: "Precio: Menor a Mayor", key: "precio", direction: "asc" },
  { label: "Precio: Mayor a Menor", key: "precio", direction: "desc" },
];

export const ALL_RECETA_COLUMNS = [
  { key: "costo", label: "Costo" },
  { key: "precio_venta", label: "Precio Venta" },
  { key: "stock_bodega", label: "Stock por Bodega" },
  { key: "consumo_dia", label: "Consumo Día" },
  { key: "consumo_semana", label: "Consumo Semanal" },
  { key: "consumo_mes", label: "Consumo Mensual" },
] as const;

export type RecetaColumnKey = (typeof ALL_RECETA_COLUMNS)[number]["key"];

export const DEFAULT_RECETA_COLUMNS: RecetaColumnKey[] = [
  "costo",
  "precio_venta",
  "stock_bodega",
  "consumo_dia",
  "consumo_semana",
  "consumo_mes",
];

export const RECETA_COLUMN_WIDTHS: Record<RecetaColumnKey, string> = {
  costo: "w-[110px]",
  precio_venta: "w-[110px]",
  stock_bodega: "w-[240px]",
  consumo_dia: "w-[90px]",
  consumo_semana: "w-[90px]",
  consumo_mes: "w-[90px]",
};

export const RECETA_SORT_OPTIONS: SortOption<"nombre" | "precio" | "stock">[] = [
  { label: "Nombre A-Z", key: "nombre", direction: "asc" },
  { label: "Nombre Z-A", key: "nombre", direction: "desc" },
  { label: "Precio: Menor a Mayor", key: "precio", direction: "asc" },
  { label: "Precio: Mayor a Menor", key: "precio", direction: "desc" },
  { label: "Stock: Menor a Mayor", key: "stock", direction: "asc" },
  { label: "Stock: Mayor a Menor", key: "stock", direction: "desc" },
];

export const ALL_COMBO_COLUMNS = [
  { key: "costo", label: "Costo" },
  { key: "precio_venta", label: "Precio Venta" },
  { key: "stock_bodega", label: "Stock Disponible" },
  { key: "consumo_dia", label: "Consumo Día" },
  { key: "consumo_semana", label: "Consumo Semanal" },
  { key: "consumo_mes", label: "Consumo Mensual" },
] as const;

export type ComboColumnKey = (typeof ALL_COMBO_COLUMNS)[number]["key"];

export const DEFAULT_COMBO_COLUMNS: ComboColumnKey[] = [
  "costo",
  "precio_venta",
  "stock_bodega",
  "consumo_dia",
  "consumo_semana",
  "consumo_mes",
];

export const COMBO_COLUMN_WIDTHS: Record<ComboColumnKey, string> = {
  costo: "w-[110px]",
  precio_venta: "w-[110px]",
  stock_bodega: "w-[180px]",
  consumo_dia: "w-[90px]",
  consumo_semana: "w-[90px]",
  consumo_mes: "w-[90px]",
};

export const SYSTEM_PRESETS: TablePreset<ColumnKey, "nombre" | "stock" | "precio" | "vigencia">[] = [
  {
    id: "system-operario",
    name: "👷 Plantilla Operario (Conteo & Reposición)",
    description: "Ideal para personal de bodega enfocados en conteos de stock y reposición rápida",
    columns: ["bodega", "ubicacion", "stock_actual", "stock_min", "contenido_total"],
    isSystem: true,
  },
  {
    id: "system-resumen",
    name: "📌 Vista Gerencial / Dashboard Resumen",
    description: "Resumen ejecutivo con precios de venta, márgenes y valorización de inventario",
    columns: [
      "stock_actual",
      "dias_cobertura",
      "ultimo_costo_unidad_neto",
      "precio_venta_bruto",
      "margen_bruto",
      "valor_inventario_neto",
    ],
    isSystem: true,
  },
  {
    id: "system-costos",
    name: "🛒 Auditoría de Compras & Inflación",
    description: "Comparativa de costos históricos, variaciones de precio e impacto inflacionario",
    columns: [
      "ultimo_costo_unidad_neto",
      "penultimo_costo_unidad_neto",
      "variacion_costo",
      "ultimo_costo_embalaje_neto",
      "penultimo_costo_embalaje_neto",
      "costo_prom_hist_unidad_neto",
    ],
    isSystem: true,
  },
  {
    id: "system-finanzas",
    name: "🏦 Finanzas, Balances & Impuestos",
    description: "Desglose financiero completo con precios neto/bruto y márgenes netos",
    columns: [
      "precio_venta_neto",
      "precio_venta_bruto",
      "margen_neto",
      "margen_bruto",
      "valor_inventario_neto",
      "valor_inventario_bruto",
    ],
    isSystem: true,
  },
  {
    id: "system-bodega",
    name: "📦 Control de Inventario & Quiebres",
    description: "Detección de quiebres de stock, días de cobertura e índice de rotación",
    columns: [
      "bodega",
      "ubicacion",
      "stock_actual",
      "stock_min",
      "contenido_total",
      "dias_cobertura",
      "indice_rotacion",
    ],
    isSystem: true,
  },
  {
    id: "system-embalajes",
    name: "📦 Comparativa Embalajes vs Unidades",
    description: "Análisis de costos de compra por cajas/embalajes frente a unidades individuales",
    columns: [
      "contenido_total",
      "ultimo_costo_unidad_neto",
      "ultimo_costo_embalaje_neto",
      "costo_prom_inv_embalaje_neto",
      "costo_prom_inv_embalaje_bruto",
    ],
    isSystem: true,
  },
];

// Interfaces para filtros y persistencia
export interface GestionFilters {
  searchQuery: string;
  categoriaId: string | null;
  bodegaId: string | null;
  areaId: string | null;
  viewTab: ViewTab;
  viewMode: ViewMode;
  estado?: string | null;
}

export interface ProductDraft {
  id?: string;
  nombre?: string;
  categoria_id?: string;
  familia_id?: string | null;
  marca_id?: string | null;
  tipo_envase_id?: string | null;
  unidad?: string;
  costo_unitario?: number;
  precio_venta?: number;
  codigo_barra?: string;
  sku?: string;
  bodegas_config?: BodegaConfig[];
  presentaciones_compra?: PresentacionCompra[];
  updatedAt: string;
}

export interface RecetaDraft {
  id?: string;
  nombre?: string;
  precio?: number;
  categoria_receta_id?: string;
  ingredientes?: IngredienteReceta[];
  updatedAt: string;
}
