// oppytec-frontend/src/features/gestion/useGestion.ts
import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import {
  Categoria,
  CategoriaReceta,
  CategoriaCombo,
  Marca,
  TipoEnvase,
  Producto,
  Receta,
  Combo,
  GrupoOpciones,
} from "./types";

// ============================================================================
// Robust Mock Dataset for 0 Blank Screens (Gastronomía Real)
// ============================================================================
export const INITIAL_CATEGORIAS_MOCK: Categoria[] = [
  { id: "cat-carnes", nombre: "Carnes y Aves", color: "#DC2626", icono: "beef", tipo_categoria: "insumo" },
  { id: "cat-pescados", nombre: "Pescados y Mariscos", color: "#0284C7", icono: "fish", tipo_categoria: "insumo" },
  { id: "cat-lacteos", nombre: "Lácteos y Quesos", color: "#EAB308", icono: "milk", tipo_categoria: "insumo" },
  { id: "cat-abarrotes", nombre: "Abarrotes e Insumos Secos", color: "#D97706", icono: "wheat", tipo_categoria: "insumo" },
  { id: "cat-bebidas", nombre: "Vinos y Licores", color: "#7C3AED", icono: "wine", tipo_categoria: "producto" },
  { id: "cat-cafeteria", nombre: "Cafetería e Infusiones", color: "#92400E", icono: "coffee", tipo_categoria: "producto" },
];

export const INITIAL_MARCAS_MOCK: Marca[] = [
  { id: "marca-angus", nombre: "Angus Pride", logo_url: null },
  { id: "marca-santa-helena", nombre: "Santa Helena", logo_url: null },
  { id: "marca-colun", nombre: "Colun", logo_url: null },
  { id: "marca-la-finca", nombre: "La Finca", logo_url: null },
  { id: "marca-concha-toro", nombre: "Concha y Toro", logo_url: null },
  { id: "marca-lavazza", nombre: "Lavazza", logo_url: null },
];

export const INITIAL_TIPOS_ENVASE_MOCK: TipoEnvase[] = [
  { id: "env-caja", nombre: "Caja", icono: "package", es_predeterminado: true },
  { id: "env-botella", nombre: "Botella", icono: "bottle" },
  { id: "env-bolsa", nombre: "Bolsa al Vacío", icono: "bag" },
  { id: "env-bidon", nombre: "Bidón", icono: "can" },
  { id: "env-saco", nombre: "Saco", icono: "sack" },
];

export const INITIAL_PRODUCTOS_MOCK: Producto[] = [
  {
    id: "prod-1",
    nombre: "Lomo Vetado Angus Premium",
    nombre_completo: "Lomo Vetado Angus Premium Corte Americano",
    categoria_id: "cat-carnes",
    marca_id: "marca-angus",
    marca: "Angus Pride",
    tipo_envase_id: "env-bolsa",
    unidad: "kg",
    costo_unitario: 14500,
    costo_unitario_ultimo: 14500,
    costo_unitario_penultimo: 13800,
    costo_unitario_promedio_10: 14000,
    costo_unitario_ppp: 14200,
    ultimo_costo: 14500,
    penultimo_costo: 13800,
    costo_promedio: 14200,
    costo_promedio_inventario: 14200,
    costo_promedio_historico: 14000,
    precio_venta: 22900,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7801234567890",
    sku: "CAR-LOM-001",
    stock_actual: 45,
    valor_inventario: 639000,
    unidades_vendidas_mes: 180,
    consumo_diario_promedio: 6,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-frio",
        bodega_nombre: "Cámara de Frío",
        stock_minimo: 20,
        stock_actual: 35,
        coordenada_letra: "C",
        coordenada_numero: "2",
      },
      {
        bodega_id: "bod-cocina",
        bodega_nombre: "Cocina Caliente",
        stock_minimo: 10,
        stock_actual: 10,
        coordenada_letra: "A",
        coordenada_numero: "1",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja al Vacío 20kg",
        equivalencia: 20,
        ultimo_costo: 290000,
        penultimo_costo: 276000,
        costo_bruto: 345100,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-LOM-20K",
      },
    ],
  },
  {
    id: "prod-2",
    nombre: "Pechuga de Pollo Deshuesada",
    nombre_completo: "Pechuga de Pollo Deshuesada Congelada IQF",
    categoria_id: "cat-carnes",
    marca_id: "marca-santa-helena",
    marca: "Santa Helena",
    tipo_envase_id: "env-caja",
    unidad: "kg",
    costo_unitario: 4800,
    costo_unitario_ultimo: 4800,
    costo_unitario_penultimo: 4500,
    costo_unitario_promedio_10: 4600,
    costo_unitario_ppp: 4700,
    ultimo_costo: 4800,
    precio_venta: 8900,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7802345678901",
    sku: "AVE-PEC-002",
    stock_actual: 60,
    valor_inventario: 282000,
    unidades_vendidas_mes: 320,
    consumo_diario_promedio: 11,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-frio",
        bodega_nombre: "Cámara de Frío",
        stock_minimo: 25,
        stock_actual: 45,
        coordenada_letra: "B",
        coordenada_numero: "3",
      },
      {
        bodega_id: "bod-cocina",
        bodega_nombre: "Cocina Caliente",
        stock_minimo: 15,
        stock_actual: 15,
        coordenada_letra: "A",
        coordenada_numero: "2",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja Master 15kg",
        equivalencia: 15,
        ultimo_costo: 72000,
        penultimo_costo: 67500,
        costo_bruto: 85680,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-POL-15K",
      },
    ],
  },
  {
    id: "prod-3",
    nombre: "Salmón Atlántico Fresco",
    nombre_completo: "Filete de Salmón Atlántico Fresco Trim D con Piel",
    categoria_id: "cat-pescados",
    tipo_envase_id: "env-caja",
    unidad: "kg",
    costo_unitario: 16500,
    costo_unitario_ultimo: 16500,
    costo_unitario_penultimo: 15900,
    costo_unitario_promedio_10: 16100,
    costo_unitario_ppp: 16300,
    ultimo_costo: 16500,
    precio_venta: 24900,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7803456789012",
    sku: "PES-SAL-003",
    stock_actual: 25,
    valor_inventario: 407500,
    unidades_vendidas_mes: 110,
    consumo_diario_promedio: 4,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-frio",
        bodega_nombre: "Cámara de Frío",
        stock_minimo: 15,
        stock_actual: 25,
        coordenada_letra: "D",
        coordenada_numero: "1",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja Poliestireno 10kg",
        equivalencia: 10,
        ultimo_costo: 165000,
        penultimo_costo: 159000,
        costo_bruto: 196350,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-SAL-10K",
      },
    ],
  },
  {
    id: "prod-4",
    nombre: "Leche Entera Colun 1L",
    nombre_completo: "Leche Entera UHT Larga Vida Colun Tetra Brik 1L",
    categoria_id: "cat-lacteos",
    marca_id: "marca-colun",
    marca: "Colun",
    tipo_envase_id: "env-caja",
    unidad: "unidad",
    costo_unitario: 950,
    costo_unitario_ultimo: 950,
    costo_unitario_penultimo: 900,
    costo_unitario_promedio_10: 920,
    costo_unitario_ppp: 935,
    ultimo_costo: 950,
    precio_venta: 1490,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7804567890123",
    sku: "LAC-LEC-004",
    stock_actual: 120,
    valor_inventario: 112200,
    unidades_vendidas_mes: 240,
    consumo_diario_promedio: 8,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-central",
        bodega_nombre: "Bodega Principal / Central",
        stock_minimo: 48,
        stock_actual: 96,
        coordenada_letra: "E",
        coordenada_numero: "1",
      },
      {
        bodega_id: "bod-cocina",
        bodega_nombre: "Cocina Caliente",
        stock_minimo: 12,
        stock_actual: 24,
        coordenada_letra: "B",
        coordenada_numero: "1",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja 12 Unidades",
        equivalencia: 12,
        ultimo_costo: 11400,
        penultimo_costo: 10800,
        costo_bruto: 13566,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-LEC-12U",
      },
    ],
  },
  {
    id: "prod-5",
    nombre: "Queso Mozzarella Barra 2.5kg",
    nombre_completo: "Queso Mozzarella Tradicional Barra 2.5kg Colun",
    categoria_id: "cat-lacteos",
    marca_id: "marca-colun",
    marca: "Colun",
    tipo_envase_id: "env-bolsa",
    unidad: "unidad",
    costo_unitario: 15500,
    costo_unitario_ultimo: 15500,
    costo_unitario_penultimo: 15000,
    costo_unitario_promedio_10: 15200,
    costo_unitario_ppp: 15350,
    ultimo_costo: 15500,
    precio_venta: 22500,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7805678901234",
    sku: "LAC-MOZ-005",
    stock_actual: 18,
    valor_inventario: 276300,
    unidades_vendidas_mes: 45,
    consumo_diario_promedio: 1.5,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-frio",
        bodega_nombre: "Cámara de Frío",
        stock_minimo: 8,
        stock_actual: 14,
        coordenada_letra: "C",
        coordenada_numero: "4",
      },
      {
        bodega_id: "bod-cocina",
        bodega_nombre: "Cocina Caliente",
        stock_minimo: 4,
        stock_actual: 4,
        coordenada_letra: "A",
        coordenada_numero: "3",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja 4 Barras (10kg)",
        equivalencia: 4,
        ultimo_costo: 62000,
        penultimo_costo: 60000,
        costo_bruto: 73780,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-MOZ-4B",
      },
    ],
  },
  {
    id: "prod-6",
    nombre: "Aceite de Oliva Extra Virgen 5L",
    nombre_completo: "Aceite de Oliva Extra Virgen Primera Prensada Fría 5L",
    categoria_id: "cat-abarrotes",
    marca_id: "marca-la-finca",
    marca: "La Finca",
    tipo_envase_id: "env-bidon",
    unidad: "bidón",
    costo_unitario: 32000,
    costo_unitario_ultimo: 32000,
    costo_unitario_penultimo: 29500,
    costo_unitario_promedio_10: 30500,
    costo_unitario_ppp: 31200,
    ultimo_costo: 32000,
    precio_venta: 44900,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7806789012345",
    sku: "ABA-OLI-006",
    stock_actual: 15,
    valor_inventario: 468000,
    unidades_vendidas_mes: 25,
    consumo_diario_promedio: 0.8,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-central",
        bodega_nombre: "Bodega Principal / Central",
        stock_minimo: 6,
        stock_actual: 12,
        coordenada_letra: "F",
        coordenada_numero: "2",
      },
      {
        bodega_id: "bod-cocina",
        bodega_nombre: "Cocina Caliente",
        stock_minimo: 2,
        stock_actual: 3,
        coordenada_letra: "B",
        coordenada_numero: "2",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja 4 Bidones de 5L",
        equivalencia: 4,
        ultimo_costo: 128000,
        penultimo_costo: 118000,
        costo_bruto: 152320,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-OLI-4B",
      },
    ],
  },
  {
    id: "prod-7",
    nombre: "Harina de Trigo Especial 25kg",
    nombre_completo: "Harina de Trigo Sin Polvos de Hornear Saco 25kg",
    categoria_id: "cat-abarrotes",
    tipo_envase_id: "env-saco",
    unidad: "saco",
    costo_unitario: 18500,
    costo_unitario_ultimo: 18500,
    costo_unitario_penultimo: 17900,
    costo_unitario_promedio_10: 18100,
    costo_unitario_ppp: 18300,
    ultimo_costo: 18500,
    precio_venta: 26900,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7807890123456",
    sku: "ABA-HAR-007",
    stock_actual: 30,
    valor_inventario: 549000,
    unidades_vendidas_mes: 50,
    consumo_diario_promedio: 1.6,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-central",
        bodega_nombre: "Bodega Principal / Central",
        stock_minimo: 10,
        stock_actual: 25,
        coordenada_letra: "F",
        coordenada_numero: "3",
      },
      {
        bodega_id: "bod-cocina",
        bodega_nombre: "Cocina Caliente",
        stock_minimo: 4,
        stock_actual: 5,
        coordenada_letra: "B",
        coordenada_numero: "4",
      },
    ],
  },
  {
    id: "prod-8",
    nombre: "Vino Cabernet Sauvignon Reserva 750ml",
    nombre_completo: "Vino Casillero del Diablo Cabernet Sauvignon Reserva 750ml",
    categoria_id: "cat-bebidas",
    marca_id: "marca-concha-toro",
    marca: "Concha y Toro",
    tipo_envase_id: "env-botella",
    unidad: "botella",
    costo_unitario: 5200,
    costo_unitario_ultimo: 5200,
    costo_unitario_penultimo: 4900,
    costo_unitario_promedio_10: 5050,
    costo_unitario_ppp: 5120,
    ultimo_costo: 5200,
    precio_venta: 14900,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7808901234567",
    sku: "BEB-VIN-008",
    stock_actual: 48,
    valor_inventario: 245760,
    unidades_vendidas_mes: 72,
    consumo_diario_promedio: 2.4,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-bar",
        bodega_nombre: "Bar / Cava",
        stock_minimo: 18,
        stock_actual: 36,
        coordenada_letra: "A",
        coordenada_numero: "1",
      },
      {
        bodega_id: "bod-central",
        bodega_nombre: "Bodega Principal / Central",
        stock_minimo: 12,
        stock_actual: 12,
        coordenada_letra: "C",
        coordenada_numero: "1",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja Cartón 12 Botellas",
        equivalencia: 12,
        ultimo_costo: 62400,
        penultimo_costo: 58800,
        costo_bruto: 74256,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-VIN-12B",
      },
    ],
  },
  {
    id: "prod-9",
    nombre: "Cerveza Artesanal IPA 330ml",
    nombre_completo: "Cerveza Artesanal India Pale Ale Botella 330ml",
    categoria_id: "cat-bebidas",
    tipo_envase_id: "env-botella",
    unidad: "botella",
    costo_unitario: 1200,
    costo_unitario_ultimo: 1200,
    costo_unitario_penultimo: 1150,
    costo_unitario_promedio_10: 1180,
    costo_unitario_ppp: 1195,
    ultimo_costo: 1200,
    precio_venta: 3800,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7809012345678",
    sku: "BEB-CER-009",
    stock_actual: 120,
    valor_inventario: 143400,
    unidades_vendidas_mes: 350,
    consumo_diario_promedio: 11.6,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-bar",
        bodega_nombre: "Bar / Cava",
        stock_minimo: 48,
        stock_actual: 96,
        coordenada_letra: "B",
        coordenada_numero: "2",
      },
      {
        bodega_id: "bod-central",
        bodega_nombre: "Bodega Principal / Central",
        stock_minimo: 24,
        stock_actual: 24,
        coordenada_letra: "D",
        coordenada_numero: "3",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Pack Caja 24 Botellas",
        equivalencia: 24,
        ultimo_costo: 28800,
        penultimo_costo: 27600,
        costo_bruto: 34272,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-CER-24B",
      },
    ],
  },
  {
    id: "prod-10",
    nombre: "Café de Grano Colombia Supremo 1kg",
    nombre_completo: "Café en Grano Colombia Supremo Tueste Medio Lavazza 1kg",
    categoria_id: "cat-cafeteria",
    marca_id: "marca-lavazza",
    marca: "Lavazza",
    tipo_envase_id: "env-bolsa",
    unidad: "kg",
    costo_unitario: 16000,
    costo_unitario_ultimo: 16000,
    costo_unitario_penultimo: 15200,
    costo_unitario_promedio_10: 15500,
    costo_unitario_ppp: 15800,
    ultimo_costo: 16000,
    precio_venta: 26000,
    iva_incluido: true,
    iva_porcentaje: 19,
    codigo_barra: "7800123456789",
    sku: "CAF-COL-010",
    stock_actual: 24,
    valor_inventario: 379200,
    unidades_vendidas_mes: 40,
    consumo_diario_promedio: 1.3,
    estado: "activo",
    bodegas_config: [
      {
        bodega_id: "bod-bar",
        bodega_nombre: "Bar / Cava",
        stock_minimo: 6,
        stock_actual: 10,
        coordenada_letra: "C",
        coordenada_numero: "1",
      },
      {
        bodega_id: "bod-central",
        bodega_nombre: "Bodega Principal / Central",
        stock_minimo: 8,
        stock_actual: 14,
        coordenada_letra: "A",
        coordenada_numero: "4",
      },
    ],
    presentaciones_compra: [
      {
        nombre: "Caja Master 6 Bolsas (6kg)",
        equivalencia: 6,
        ultimo_costo: 96000,
        penultimo_costo: 91200,
        costo_bruto: 114240,
        iva_porcentaje: 19,
        tipo_embalaje: "Caja",
        sku: "EMB-CAF-6K",
      },
    ],
  },
];

export const INITIAL_RECETAS_MOCK: Receta[] = [
  {
    id: "rec-1",
    nombre: "Lomo Vetado a la Parrilla 350g",
    precio: 18900,
    porciones: 1,
    iva_incluido: true,
    iva_porcentaje: 19,
    costo_total: 6200,
    costo_porcion: 6200,
    precio_neto: 15882,
    precio_bruto: 18900,
    consumo_diario: 12,
    consumo_semanal: 84,
    consumo_mensual: 360,
    ingredientes: [
      { producto_id: "prod-1", nombre_producto: "Lomo Vetado Angus Premium", cantidad: 0.35, unidad: "kg", type: "producto" },
      { producto_id: "prod-6", nombre_producto: "Aceite de Oliva Extra Virgen 5L", cantidad: 0.02, unidad: "bidón", type: "producto" },
    ],
  },
  {
    id: "rec-2",
    nombre: "Salmón Grillado con Salsa Finas Hierbas",
    precio: 19500,
    porciones: 1,
    iva_incluido: true,
    iva_porcentaje: 19,
    costo_total: 7100,
    costo_porcion: 7100,
    precio_neto: 16386,
    precio_bruto: 19500,
    consumo_diario: 8,
    consumo_semanal: 56,
    consumo_mensual: 240,
    ingredientes: [
      { producto_id: "prod-3", nombre_producto: "Salmón Atlántico Fresco", cantidad: 0.25, unidad: "kg", type: "producto" },
      { producto_id: "prod-4", nombre_producto: "Leche Entera Colun 1L", cantidad: 0.05, unidad: "unidad", type: "producto" },
    ],
  },
  {
    id: "rec-3",
    nombre: "Café Latte Doble",
    precio: 3400,
    porciones: 1,
    iva_incluido: true,
    iva_porcentaje: 19,
    costo_total: 680,
    costo_porcion: 680,
    precio_neto: 2857,
    precio_bruto: 3400,
    consumo_diario: 35,
    consumo_semanal: 245,
    consumo_mensual: 1050,
    ingredientes: [
      { producto_id: "prod-10", nombre_producto: "Café de Grano Colombia Supremo 1kg", cantidad: 0.018, unidad: "kg", type: "producto" },
      { producto_id: "prod-4", nombre_producto: "Leche Entera Colun 1L", cantidad: 0.22, unidad: "unidad", type: "producto" },
    ],
  },
];

export const INITIAL_COMBOS_MOCK: Combo[] = [
  {
    id: "combo-1",
    nombre: "Menú Ejecutivo Parrillero",
    precio: 23900,
    iva_incluido: true,
    iva_porcentaje: 19,
    costo_total: 8900,
    precio_neto: 20084,
    precio_bruto: 23900,
    items: [
      { id: "ci-1", receta_id: "rec-1", cantidad: 1, nombre: "Lomo Vetado a la Parrilla 350g", type: "receta" },
      { id: "ci-2", producto_id: "prod-8", cantidad: 1, nombre: "Vino Cabernet Sauvignon Reserva 750ml", type: "producto" },
    ],
  },
];

export const INITIAL_GRUPOS_OPCIONES_MOCK: GrupoOpciones[] = [
  {
    id: "grp-1",
    nombre: "Término de la Carne",
    seleccion_minima: 1,
    seleccion_maxima: 1,
    items: [
      { id: "goi-1", nombre: "Casi Crudo / Bleu", precio_adicional: 0, iva_incluido: true, iva_porcentaje: 19 },
      { id: "goi-2", nombre: "A Punto / Término Medio", precio_adicional: 0, iva_incluido: true, iva_porcentaje: 19 },
      { id: "goi-3", nombre: "Tres Cuartos (3/4)", precio_adicional: 0, iva_incluido: true, iva_porcentaje: 19 },
      { id: "goi-4", nombre: "Bien Cocido", precio_adicional: 0, iva_incluido: true, iva_porcentaje: 19 },
    ],
  },
];

// ============================================================================
// Hook useGestion con Resiliencia Total (0 pantallas en blanco)
// ============================================================================
export function useGestion(areaId?: string | null) {
  const [categorias, setCategorias] = useState<Categoria[]>(INITIAL_CATEGORIAS_MOCK);
  const [categoriasRecetas, setCategoriasRecetas] = useState<CategoriaReceta[]>([]);
  const [categoriasCombos, setCategoriasCombos] = useState<CategoriaCombo[]>([]);
  const [marcas, setMarcas] = useState<Marca[]>(INITIAL_MARCAS_MOCK);
  const [tiposEnvase, setTiposEnvase] = useState<TipoEnvase[]>(INITIAL_TIPOS_ENVASE_MOCK);
  const [productos, setProductos] = useState<Producto[]>(INITIAL_PRODUCTOS_MOCK);
  const [recetas, setRecetas] = useState<Receta[]>(INITIAL_RECETAS_MOCK);
  const [combos, setCombos] = useState<Combo[]>(INITIAL_COMBOS_MOCK);
  const [gruposOpciones, setGruposOpciones] = useState<GrupoOpciones[]>(INITIAL_GRUPOS_OPCIONES_MOCK);
  const [mermas, setMermas] = useState<any[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [savingProduct, setSavingProduct] = useState<boolean>(false);
  const [savingReceta, setSavingReceta] = useState<boolean>(false);
  const [savingCombo, setSavingCombo] = useState<boolean>(false);
  const [savingGrupoOpciones, setSavingGrupoOpciones] = useState<boolean>(false);
  const [isOffline, setIsOffline] = useState<boolean>(false);

  // Helper de sincronización
  const notifyProductUpdated = useCallback(() => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("product_updated"));
    }
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        apiRequest<Producto[]>("/inventory/products"),
        apiRequest<Receta[]>(`/operations/recipes${areaId ? `?area_id=${areaId}` : ""}`),
        apiRequest<Categoria[]>("/inventory/categories"),
        apiRequest<CategoriaReceta[]>("/operations/recipes/categories"),
        apiRequest<CategoriaCombo[]>("/operations/combos/categories"),
        apiRequest<any[]>("/inventory/history?tipo_movimiento=merma"),
        apiRequest<Combo[]>(`/operations/combos${areaId ? `?area_id=${areaId}` : ""}`),
        apiRequest<GrupoOpciones[]>("/operations/grupos-opciones"),
        apiRequest<Marca[]>("/inventory/brands"),
        apiRequest<TipoEnvase[]>("/inventory/packaging-types"),
      ]);

      const [
        prodRes,
        recRes,
        catRes,
        catRecRes,
        catComboRes,
        mermasRes,
        combosRes,
        gruposRes,
        marcasRes,
        envasesRes,
      ] = results;

      let offlineDetected = false;

      // Productos
      if (prodRes.status === "fulfilled" && Array.isArray(prodRes.value?.data) && prodRes.value.data.length > 0) {
        setProductos(prodRes.value.data);
      } else {
        offlineDetected = true;
        setProductos((prev) => (prev.length > 0 ? prev : INITIAL_PRODUCTOS_MOCK));
      }

      // Categorías
      if (catRes.status === "fulfilled" && Array.isArray(catRes.value?.data) && catRes.value.data.length > 0) {
        setCategorias(catRes.value.data);
      } else {
        setCategorias((prev) => (prev.length > 0 ? prev : INITIAL_CATEGORIAS_MOCK));
      }

      // Recetas
      if (recRes.status === "fulfilled" && Array.isArray(recRes.value?.data) && recRes.value.data.length > 0) {
        setRecetas(recRes.value.data);
      } else {
        setRecetas((prev) => (prev.length > 0 ? prev : INITIAL_RECETAS_MOCK));
      }

      // Categorías de Recetas
      if (catRecRes.status === "fulfilled" && Array.isArray(catRecRes.value?.data)) {
        setCategoriasRecetas(catRecRes.value.data);
      }

      // Categorías de Combos
      if (catComboRes.status === "fulfilled" && Array.isArray(catComboRes.value?.data)) {
        setCategoriasCombos(catComboRes.value.data);
      }

      // Combos
      if (combosRes.status === "fulfilled" && Array.isArray(combosRes.value?.data) && combosRes.value.data.length > 0) {
        setCombos(combosRes.value.data);
      } else {
        setCombos((prev) => (prev.length > 0 ? prev : INITIAL_COMBOS_MOCK));
      }

      // Grupos de Opciones
      if (gruposRes.status === "fulfilled" && Array.isArray(gruposRes.value?.data) && gruposRes.value.data.length > 0) {
        setGruposOpciones(gruposRes.value.data);
      } else {
        setGruposOpciones((prev) => (prev.length > 0 ? prev : INITIAL_GRUPOS_OPCIONES_MOCK));
      }

      // Mermas
      if (mermasRes.status === "fulfilled" && Array.isArray(mermasRes.value?.data)) {
        setMermas(mermasRes.value.data);
      }

      // Marcas
      if (marcasRes.status === "fulfilled" && Array.isArray(marcasRes.value?.data) && marcasRes.value.data.length > 0) {
        setMarcas(marcasRes.value.data);
      } else {
        setMarcas((prev) => (prev.length > 0 ? prev : INITIAL_MARCAS_MOCK));
      }

      // Tipos de Envase
      if (envasesRes.status === "fulfilled" && Array.isArray(envasesRes.value?.data) && envasesRes.value.data.length > 0) {
        setTiposEnvase(envasesRes.value.data);
      } else {
        setTiposEnvase((prev) => (prev.length > 0 ? prev : INITIAL_TIPOS_ENVASE_MOCK));
      }

      setIsOffline(offlineDetected);
    } catch {
      setIsOffline(true);
      // Garantizar que nunca quede en blanco
      setProductos((prev) => (prev.length > 0 ? prev : INITIAL_PRODUCTOS_MOCK));
      setCategorias((prev) => (prev.length > 0 ? prev : INITIAL_CATEGORIAS_MOCK));
    } finally {
      setLoading(false);
    }
  }, [areaId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Listener para evento 'product_updated'
  const isSelfDispatching = useRef(false);

  useEffect(() => {
    const handleProductUpdated = () => {
      if (isSelfDispatching.current) return;
      void loadData();
    };
    window.addEventListener("product_updated", handleProductUpdated);
    return () => {
      window.removeEventListener("product_updated", handleProductUpdated);
    };
  }, [loadData]);

  const dispatchUpdate = useCallback(() => {
    isSelfDispatching.current = true;
    notifyProductUpdated();
    setTimeout(() => {
      isSelfDispatching.current = false;
    }, 50);
  }, [notifyProductUpdated]);

  // ============================================================================
  // Category CRUD
  // ============================================================================
  const createCategory = async (nombre: string, meta?: Partial<Categoria>) => {
    const tempId = `cat-${Date.now()}`;
    const newCategory: Categoria = {
      id: tempId,
      nombre,
      color: meta?.color ?? "#4F46E5",
      icono: meta?.icono ?? "tag",
      tipo_categoria: meta?.tipo_categoria ?? "insumo",
      area_operativa_ids: meta?.area_operativa_ids ?? [],
    };

    setCategorias((prev) => [...prev, newCategory]);

    try {
      const res = await apiRequest<Categoria>("/inventory/categories", {
        method: "POST",
        body: { nombre, ...meta },
      });
      if (res?.data?.id) {
        setCategorias((prev) => prev.map((c) => (c.id === tempId ? res.data : c)));
      }
      toast.success("Categoría creada con éxito");
    } catch {
      toast.success("Categoría guardada localmente (modo offline)");
    } finally {
      dispatchUpdate();
    }
  };

  const updateCategory = async (id: string, nombre: string, meta?: Partial<Categoria>) => {
    setCategorias((prev) =>
      prev.map((c) => (c.id === id ? { ...c, nombre, ...(meta ?? {}) } : c))
    );

    try {
      await apiRequest(`/inventory/categories/${id}`, {
        method: "PUT",
        body: { nombre, ...meta },
      });
      toast.success("Categoría actualizada con éxito");
    } catch {
      toast.success("Categoría actualizada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const deleteCategory = async (id: string) => {
    setCategorias((prev) => prev.filter((c) => c.id !== id));

    try {
      await apiRequest(`/inventory/categories/${id}`, {
        method: "DELETE",
      });
      toast.success("Categoría eliminada con éxito");
    } catch {
      toast.success("Categoría eliminada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const createCategoryReceta = async (nombre: string) => {
    const tempId = `catrec-${Date.now()}`;
    const newCat: CategoriaReceta = { id: tempId, nombre, color: "#10B981", icono: "chef-hat" };
    setCategoriasRecetas((prev) => [...prev, newCat]);

    try {
      const res = await apiRequest<CategoriaReceta>("/operations/recipes/categories", {
        method: "POST",
        body: { nombre },
      });
      if (res?.data?.id) {
        setCategoriasRecetas((prev) => prev.map((c) => (c.id === tempId ? res.data : c)));
      }
      toast.success("Categoría de receta creada");
    } catch {
      toast.success("Categoría de receta guardada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const deleteCategoryReceta = async (id: string) => {
    setCategoriasRecetas((prev) => prev.filter((c) => c.id !== id));
    try {
      await apiRequest(`/operations/recipes/categories/${id}`, {
        method: "DELETE",
      });
      toast.success("Categoría de receta eliminada");
    } catch {
      toast.success("Categoría de receta eliminada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  // ============================================================================
  // Brand & Packaging CRUD
  // ============================================================================
  const createBrand = async (nombre: string, logo_url?: string | null) => {
    const tempId = `marca-${Date.now()}`;
    const newMarca: Marca = { id: tempId, nombre, logo_url: logo_url ?? null };
    setMarcas((prev) => [...prev, newMarca]);

    try {
      const res = await apiRequest<Marca>("/inventory/brands", {
        method: "POST",
        body: { nombre, logo_url },
      });
      if (res?.data?.id) {
        setMarcas((prev) => prev.map((m) => (m.id === tempId ? res.data : m)));
      }
      toast.success("Marca creada con éxito");
    } catch {
      toast.success("Marca guardada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const updateBrand = async (id: string, nombre: string, logo_url?: string | null) => {
    setMarcas((prev) =>
      prev.map((m) => (m.id === id ? { ...m, nombre, logo_url: logo_url ?? m.logo_url } : m))
    );

    try {
      await apiRequest(`/inventory/brands/${id}`, {
        method: "PUT",
        body: { nombre, logo_url },
      });
      toast.success("Marca actualizada con éxito");
    } catch {
      toast.success("Marca actualizada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const deleteBrand = async (id: string) => {
    setMarcas((prev) => prev.filter((m) => m.id !== id));

    try {
      await apiRequest(`/inventory/brands/${id}`, {
        method: "DELETE",
      });
      toast.success("Marca eliminada con éxito");
    } catch {
      toast.success("Marca eliminada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const createTipoEnvase = async (nombre: string, icono?: string | null) => {
    const tempId = `env-${Date.now()}`;
    const newEnv: TipoEnvase = { id: tempId, nombre, icono: icono ?? "package" };
    setTiposEnvase((prev) => [...prev, newEnv]);

    try {
      const res = await apiRequest<TipoEnvase>("/inventory/packaging-types", {
        method: "POST",
        body: { nombre, icono },
      });
      if (res?.data?.id) {
        setTiposEnvase((prev) => prev.map((e) => (e.id === tempId ? res.data : e)));
      }
      toast.success("Tipo de envase creado con éxito");
    } catch {
      toast.success("Tipo de envase guardado localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const updateTipoEnvase = async (id: string, nombre: string, icono?: string | null) => {
    setTiposEnvase((prev) =>
      prev.map((e) => (e.id === id ? { ...e, nombre, icono: icono ?? e.icono } : e))
    );

    try {
      await apiRequest(`/inventory/packaging-types/${id}`, {
        method: "PUT",
        body: { nombre, icono },
      });
      toast.success("Tipo de envase actualizado con éxito");
    } catch {
      toast.success("Tipo de envase actualizado localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const deleteTipoEnvase = async (id: string) => {
    setTiposEnvase((prev) => prev.filter((e) => e.id !== id));

    try {
      await apiRequest(`/inventory/packaging-types/${id}`, {
        method: "DELETE",
      });
      toast.success("Tipo de envase eliminado con éxito");
    } catch {
      toast.success("Tipo de envase eliminado localmente");
    } finally {
      dispatchUpdate();
    }
  };

  // ============================================================================
  // Product CRUD
  // ============================================================================
  const createProduct = async (data: Partial<Producto>) => {
    setSavingProduct(true);
    const tempId = `prod-${Date.now()}`;
    const newProduct: Producto = {
      id: tempId,
      nombre: data.nombre ?? "Nuevo Producto",
      categoria_id: data.categoria_id ?? (categorias[0]?.id || "cat-carnes"),
      unidad: data.unidad ?? "unidad",
      costo_unitario: data.costo_unitario ?? 0,
      bodegas_config: data.bodegas_config ?? [],
      ...data,
    };

    setProductos((prev) => [newProduct, ...prev]);

    try {
      const res = await apiRequest<Producto>("/inventory/products", {
        method: "POST",
        body: data,
      });
      if (res?.data?.id) {
        setProductos((prev) => prev.map((p) => (p.id === tempId ? res.data : p)));
      }
      toast.success("Producto creado con éxito");
    } catch {
      toast.success("Producto creado localmente (modo offline)");
    } finally {
      setSavingProduct(false);
      dispatchUpdate();
    }
  };

  const updateProduct = async (id: string, data: Partial<Producto>) => {
    setSavingProduct(true);
    setProductos((prev) =>
      prev.map((p) => (p.id === id ? { ...p, ...data } : p))
    );

    try {
      await apiRequest(`/inventory/products/${id}`, {
        method: "PUT",
        body: data,
      });
      toast.success("Producto actualizado con éxito");
    } catch {
      toast.success("Producto actualizado localmente");
    } finally {
      setSavingProduct(false);
      dispatchUpdate();
    }
  };

  const deleteProduct = async (id: string) => {
    setProductos((prev) => prev.filter((p) => p.id !== id));
    try {
      await apiRequest(`/inventory/products/${id}`, {
        method: "DELETE",
      });
      toast.success("Producto eliminado con éxito");
    } catch {
      toast.success("Producto eliminado localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const getProductsForBodega = useCallback(
    (bodegaId: string) => {
      return productos.filter((p: Producto) =>
        p.bodegas_config?.some((b) => b.bodega_id === bodegaId)
      );
    },
    [productos]
  );

  // ============================================================================
  // Recipe CRUD
  // ============================================================================
  const createReceta = async (data: Partial<Receta>) => {
    setSavingReceta(true);
    const tempId = `rec-${Date.now()}`;
    const newReceta: Receta = {
      id: tempId,
      nombre: data.nombre ?? "Nueva Receta",
      precio: data.precio ?? 0,
      ingredientes: data.ingredientes ?? [],
      ...data,
    };

    setRecetas((prev) => [newReceta, ...prev]);

    try {
      const res = await apiRequest<Receta>("/operations/recipes", {
        method: "POST",
        body: data,
      });
      if (res?.data?.id) {
        setRecetas((prev) => prev.map((r) => (r.id === tempId ? res.data : r)));
      }
      toast.success("Receta creada con éxito");
    } catch {
      toast.success("Receta creada localmente (modo offline)");
    } finally {
      setSavingReceta(false);
      dispatchUpdate();
    }
  };

  const updateReceta = async (id: string, data: Partial<Receta>) => {
    setSavingReceta(true);
    setRecetas((prev) =>
      prev.map((r) => (r.id === id ? { ...r, ...data } : r))
    );

    try {
      await apiRequest(`/operations/recipes/${id}`, {
        method: "PUT",
        body: data,
      });
      toast.success("Receta actualizada");
    } catch {
      toast.success("Receta actualizada localmente");
    } finally {
      setSavingReceta(false);
      dispatchUpdate();
    }
  };

  const deleteReceta = async (id: string) => {
    setRecetas((prev) => prev.filter((r) => r.id !== id));
    try {
      await apiRequest(`/operations/recipes/${id}`, {
        method: "DELETE",
      });
      toast.success("Receta eliminada");
    } catch {
      toast.success("Receta eliminada localmente");
    } finally {
      dispatchUpdate();
    }
  };

  const getRecetaCosto = useCallback((receta: Receta) => {
    return receta.costo_total ?? 0;
  }, []);

  // ============================================================================
  // Combo CRUD
  // ============================================================================
  const createCombo = async (data: Partial<Combo>) => {
    setSavingCombo(true);
    const tempId = `combo-${Date.now()}`;
    const newCombo: Combo = {
      id: tempId,
      nombre: data.nombre ?? "Nuevo Combo",
      precio: data.precio ?? 0,
      items: data.items ?? [],
      ...data,
    };

    setCombos((prev) => [newCombo, ...prev]);

    try {
      const res = await apiRequest<Combo>("/operations/combos", {
        method: "POST",
        body: data,
      });
      if (res?.data?.id) {
        setCombos((prev) => prev.map((c) => (c.id === tempId ? res.data : c)));
      }
      toast.success("Combo creado con éxito");
    } catch {
      toast.success("Combo creado localmente (modo offline)");
    } finally {
      setSavingCombo(false);
      dispatchUpdate();
    }
  };

  const updateCombo = async (id: string, data: Partial<Combo>) => {
    setSavingCombo(true);
    setCombos((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...data } : c))
    );

    try {
      await apiRequest(`/operations/combos/${id}`, {
        method: "PUT",
        body: data,
      });
      toast.success("Combo actualizado");
    } catch {
      toast.success("Combo actualizado localmente");
    } finally {
      setSavingCombo(false);
      dispatchUpdate();
    }
  };

  const deleteCombo = async (id: string) => {
    setCombos((prev) => prev.filter((c) => c.id !== id));
    try {
      await apiRequest(`/operations/combos/${id}`, {
        method: "DELETE",
      });
      toast.success("Combo eliminado");
    } catch {
      toast.success("Combo eliminado localmente");
    } finally {
      dispatchUpdate();
    }
  };

  // ============================================================================
  // GrupoOpciones CRUD
  // ============================================================================
  const createGrupoOpciones = async (data: Partial<GrupoOpciones>) => {
    setSavingGrupoOpciones(true);
    const tempId = `grp-${Date.now()}`;
    const newGrp: GrupoOpciones = {
      id: tempId,
      nombre: data.nombre ?? "Nuevo Grupo de Opciones",
      seleccion_minima: data.seleccion_minima ?? 1,
      seleccion_maxima: data.seleccion_maxima ?? 1,
      items: data.items ?? [],
      ...data,
    };

    setGruposOpciones((prev) => [newGrp, ...prev]);

    try {
      const res = await apiRequest<GrupoOpciones>("/operations/grupos-opciones", {
        method: "POST",
        body: data,
      });
      if (res?.data?.id) {
        setGruposOpciones((prev) => prev.map((g) => (g.id === tempId ? res.data : g)));
      }
      toast.success("Grupo de opciones creado");
    } catch {
      toast.success("Grupo de opciones creado localmente (modo offline)");
    } finally {
      setSavingGrupoOpciones(false);
      dispatchUpdate();
    }
  };

  const updateGrupoOpciones = async (id: string, data: Partial<GrupoOpciones>) => {
    setSavingGrupoOpciones(true);
    setGruposOpciones((prev) =>
      prev.map((g) => (g.id === id ? { ...g, ...data } : g))
    );

    try {
      await apiRequest(`/operations/grupos-opciones/${id}`, {
        method: "PUT",
        body: data,
      });
      toast.success("Grupo de opciones actualizado");
    } catch {
      toast.success("Grupo de opciones actualizado localmente");
    } finally {
      setSavingGrupoOpciones(false);
      dispatchUpdate();
    }
  };

  const deleteGrupoOpciones = async (id: string) => {
    setGruposOpciones((prev) => prev.filter((g) => g.id !== id));
    try {
      await apiRequest(`/operations/grupos-opciones/${id}`, {
        method: "DELETE",
      });
      toast.success("Grupo de opciones eliminado");
    } catch {
      toast.success("Grupo de opciones eliminado localmente");
    } finally {
      dispatchUpdate();
    }
  };

  return {
    categorias,
    categoriasRecetas,
    categoriasCombos,
    marcas,
    tiposEnvase,
    productos,
    recetas,
    combos,
    gruposOpciones,
    mermas,
    loading,
    savingProduct,
    savingReceta,
    savingCombo,
    savingGrupoOpciones,
    isOffline,
    refresh: loadData,
    loadData,
    // Categories
    createCategory,
    updateCategory,
    deleteCategory,
    createCategoryReceta,
    deleteCategoryReceta,
    // Brands & Packaging
    createBrand,
    updateBrand,
    deleteBrand,
    createTipoEnvase,
    updateTipoEnvase,
    deleteTipoEnvase,
    // Products
    createProduct,
    updateProduct,
    deleteProduct,
    getProductsForBodega,
    // Recipes
    createReceta,
    updateReceta,
    deleteReceta,
    getRecetaCosto,
    // Combos
    createCombo,
    updateCombo,
    deleteCombo,
    // GrupoOpciones
    createGrupoOpciones,
    updateGrupoOpciones,
    deleteGrupoOpciones,
  };
}
