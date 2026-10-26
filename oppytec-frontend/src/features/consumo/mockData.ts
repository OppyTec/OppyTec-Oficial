// oppytec-frontend/src/features/consumo/mockData.ts
import type {
  CategoriaConsumo,
  ProductoConsumo,
  RecetaConsumo,
  ComboConsumo,
  ConsumoTemplate,
  ConsumptionRecord,
  WorkerStation,
  VoiceOrderLog,
  BuffetSession,
  BuffetTemplate,
} from "./types";

export const MOCK_CATEGORIAS_CONSUMO: CategoriaConsumo[] = [
  { id: "cat-carnes", nombre: "Carnes y Aves", color: "#ef4444", icono: "Beef" },
  { id: "cat-lacteos", nombre: "Lácteos y Quesos", color: "#3b82f6", icono: "Milk" },
  { id: "cat-verduras", nombre: "Verduras y Frutas", color: "#22c55e", icono: "Salad" },
  { id: "cat-abarrotes", nombre: "Abarrotes y Secos", color: "#f59e0b", icono: "Package" },
  { id: "cat-bebidas", nombre: "Bebidas y Licores", color: "#8b5cf6", icono: "Wine" },
];

export const MOCK_PRODUCTOS_CONSUMO: ProductoConsumo[] = [
  {
    id: "prod-salm-01",
    nombre: "Salmón Fresco Filete",
    unidad: "kg",
    categoria_id: "cat-carnes",
    sku: "SALM-001",
    stock_minimo: 5,
    costo_unitario: 12500,
    precio_venta: 18500,
    stock_disponible: 14.5,
    dias_alerta_vencimiento: 7,
    lotes: [
      { lote_codigo: "LOT-SALM-A1", fecha_vencimiento: "2026-11-15", cantidad: 9.5 },
      { lote_codigo: "LOT-SALM-A2", fecha_vencimiento: "2026-11-20", cantidad: 5.0 },
    ],
  },
  {
    id: "prod-queso-parm",
    nombre: "Queso Parmesano Reggiano",
    unidad: "kg",
    categoria_id: "cat-lacteos",
    sku: "PARM-002",
    stock_minimo: 3,
    costo_unitario: 16000,
    precio_venta: 22000,
    stock_disponible: 8.0,
    dias_alerta_vencimiento: 15,
    lotes: [
      { lote_codigo: "LOT-PARM-01", fecha_vencimiento: "2026-12-01", cantidad: 8.0 },
    ],
  },
  {
    id: "prod-leche-ent",
    nombre: "Leche Entera 1L",
    unidad: "litro",
    categoria_id: "cat-lacteos",
    sku: "LEC-003",
    stock_minimo: 10,
    costo_unitario: 950,
    precio_venta: 1400,
    stock_disponible: 32,
    dias_alerta_vencimiento: 5,
    lotes: [
      { lote_codigo: "LOT-LEC-VENC", fecha_vencimiento: "2026-01-01", cantidad: 4 }, // lote vencido para testing de contingencias
      { lote_codigo: "LOT-LEC-FRESCO", fecha_vencimiento: "2026-12-10", cantidad: 28 },
    ],
  },
  {
    id: "prod-papas-gran",
    nombre: "Papas Granel Lavadas",
    unidad: "kg",
    categoria_id: "cat-verduras",
    sku: "PAP-004",
    stock_minimo: 20,
    costo_unitario: 700,
    precio_venta: 1200,
    stock_disponible: 45.0,
    dias_alerta_vencimiento: 10,
    lotes: [
      { lote_codigo: "LOT-PAP-01", fecha_vencimiento: "2026-11-30", cantidad: 45.0 },
    ],
  },
  {
    id: "prod-harina-000",
    nombre: "Harina 000 Especial",
    unidad: "kg",
    categoria_id: "cat-abarrotes",
    sku: "HAR-005",
    stock_minimo: 15,
    costo_unitario: 850,
    precio_venta: 1300,
    stock_disponible: 0, // Sin stock para probar out_of_stock
    dias_alerta_vencimiento: 30,
    lotes: [],
  },
];

export const MOCK_RECETAS_CONSUMO: RecetaConsumo[] = [
  {
    id: "rec-salmon-parmesano",
    nombre: "Salmón al Parmesano",
    precio: 16500,
    porciones: 1,
    costo_total: 4800,
    ingredientes: [
      { producto_id: "prod-salm-01", cantidad: 0.25, unidad: "kg", bodega_id: "1" },
      { producto_id: "prod-queso-parm", cantidad: 0.05, unidad: "kg", bodega_id: "1" },
    ],
    disponibilidad_por_bodega: [
      { bodega_id: "1", bodega_nombre: "Bodega Cocina Central", cantidad: 58 },
    ],
  },
  {
    id: "rec-pure-papas",
    nombre: "Puré de Papas Rústico",
    precio: 4500,
    porciones: 1,
    costo_total: 650,
    ingredientes: [
      { producto_id: "prod-papas-gran", cantidad: 0.3, unidad: "kg", bodega_id: "1" },
      { producto_id: "prod-leche-ent", cantidad: 0.1, unidad: "litro", bodega_id: "1" },
    ],
    disponibilidad_por_bodega: [
      { bodega_id: "1", bodega_nombre: "Bodega Cocina Central", cantidad: 150 },
    ],
  },
];

export const MOCK_COMBOS_CONSUMO: ComboConsumo[] = [
  {
    id: "combo-ejecutivo-mar",
    nombre: "Menú Ejecutivo Mar y Tierra",
    precio: 19990,
    disponibilidad: 40,
    items: [
      { id: "c-it-1", type: "receta", receta_id: "rec-salmon-parmesano", cantidad: 1, nombre: "Salmón al Parmesano" },
      { id: "c-it-2", type: "receta", receta_id: "rec-pure-papas", cantidad: 1, nombre: "Puré de Papas Rústico" },
    ],
  },
];

export const MOCK_TEMPLATES_CONSUMO: ConsumoTemplate[] = [
  {
    id: "tmpl-turno-manana",
    name: "Apertura Cocina Mañana",
    description: "Insumos recurrentes de apertura matutina",
    isPublic: true,
    columnsCount: 8,
    productIds: ["prod-salm-01", "prod-queso-parm", "prod-leche-ent"],
    sortMode: "alpha_asc",
  },
];

export const MOCK_CONSUMPTION_RECORDS: ConsumptionRecord[] = [
  {
    id: "rec-1001",
    codigo_folio: "FOL-20261025-001",
    bodega_id: "1",
    usuario_id: 1,
    usuario_nombre: "Chef Ejecutivo",
    tipo_origen: "MANUAL_TERMINAL",
    costo_total: 25000,
    estado: "CONFIRMADO",
    created_at: "2026-10-25T14:30:00Z",
    notas: "Consumo de servicio almuerzo",
    items: [
      {
        id: "item-1",
        tipo_item: "producto",
        item_id: "prod-salm-01",
        cantidad: 2.0,
        unidad_medida: "kg",
        costo_unitario_ppp: 12500,
        costo_total: 25000,
        lote_codigo: "LOT-SALM-A1",
      },
    ],
  },
];

export const MOCK_VOICE_STATIONS: WorkerStation[] = [
  {
    id: 1,
    name: "Estación Parrilla y Carnes",
    username: "parrilla_1",
    voice_command: "estacion carnes",
    role: "Parrillero",
    active: true,
  },
  {
    id: 2,
    name: "Estación Barra y Coctelería",
    username: "barra_1",
    voice_command: "estacion barra",
    role: "Bartender",
    active: true,
  },
];

export const MOCK_VOICE_ORDERS: VoiceOrderLog[] = [
  {
    solicitud_id: "voice-ord-001",
    timestamp: "2026-10-25T15:00:00Z",
    worker: { id: 1, name: "Parrillero Jefe", voice_command: "estacion carnes" },
    action_type: "consumo",
    item: { name: "Salmón Fresco Filete", quantity: 2, unit: "kg" },
    spoken_feedback: "Registrado 2 kg de Salmón Fresco Filete",
    transcript: "Oppy consumo 2 kilos de salmon filete",
    confidence: 0.96,
    status: "CONFIRMADO",
  },
];

export const MOCK_BUFFET_SESSIONS: BuffetSession[] = [
  {
    id: "buffet-ses-001",
    nombre: "Desayuno Buffet Ejecutivo",
    tipo_servicio: "DESAYUNO",
    bodega_id: "1",
    usuario_creador_id: 1,
    estado: "abierto",
    pax_comensales: 45,
    costo_total_montaje: 120000,
    valor_sobrante_reutilizable: 30000,
    costo_neto_pax: 2000,
    created_at: "2026-10-25T07:00:00Z",
    updated_at: "2026-10-25T10:30:00Z",
    estaciones: [
      {
        id: "st-calientes",
        nombre_estacion: "Estación Calientes & Huevos",
        orden: 1,
      },
    ],
    items: [
      {
        id: "b-it-1",
        item_type: "producto",
        producto_id: "prod-queso-parm",
        nombre: "Queso Parmesano Reggiano",
        unidad: "kg",
        cantidad_apertura: 2,
        cantidad_reposiciones: 1,
        cantidad_cierre: 0.5,
        cantidad_consumida: 2.5,
        cantidad_sobrante: 0.5,
        accion_sobrante: "retornar",
        costo_unitario_ppp: 16000,
        costo_total: 40000,
      },
    ],
  },
];

export const MOCK_BUFFET_TEMPLATES: BuffetTemplate[] = [
  {
    id: "tmpl-buffet-continental",
    nombre: "Buffet Desayuno Continental Estándar",
    descripcion: "Montaje de 3 estaciones para 60 comensales",
    isPublic: true,
    isSystem: true,
    estaciones: ["Panadería y Frutas", "Lácteos y Cereales", "Platos Calientes"],
  },
];
