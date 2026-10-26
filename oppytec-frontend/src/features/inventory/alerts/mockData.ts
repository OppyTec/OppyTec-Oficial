// oppytec-frontend/src/features/inventory/alerts/mockData.ts
import type {
  AlertsSummary,
  AlertBadge,
  CriticalStockAlert,
  ExpiredLotAlert,
  UpcomingExpiryAlert,
  AlertProductItem,
} from "./types";

/**
 * Empty state for inventory alerts (when all stock is optimal and no lots are expired/upcoming).
 */
export const MOCK_ALERTS_EMPTY: AlertsSummary = {
  total_count: 0,
  critical_count: 0,
  expired_count: 0,
  upcoming_count: 0,
  has_critical: false,
  total_financial_risk: 0,
  critical_stock: [],
  expired_lots: [],
  upcoming_expiries: [],
};

export const MOCK_ALERTS_BADGE_EMPTY: AlertBadge = {
  total_count: 0,
  has_critical: false,
  critical_stock_count: 0,
  expired_count: 0,
  upcoming_count: 0,
};

/**
 * Canonical test dataset for Critical Stock Alerts (quiebres y bajo mínimo).
 */
export const MOCK_CRITICAL_STOCK: readonly CriticalStockAlert[] = [
  {
    producto_id: 101,
    bodega_id: 1,
    bodega_nombre: "Bodega Cocina Central",
    producto_nombre: "Pechuga de Pollo Fresca",
    stock_actual: 4.5,
    stock_minimo: 25.0,
    unidad_medida: "kg",
    ratio: {
      stock_actual: 4.5,
      stock_minimo: 25.0,
      raw_ratio: 18.0,
      clamped_ratio: 18.0,
      status: "critical",
    },
    is_depleted: false,
    bodega_color: "#3B82F6",
    bodega_icono: "warehouse",
    costo_promedio: 4800,
  },
  {
    producto_id: 102,
    bodega_id: 2,
    bodega_nombre: "Cámara Fría -18°C",
    producto_nombre: "Aceite de Oliva Extra Virgen",
    stock_actual: 0.0,
    stock_minimo: 10.0,
    unidad_medida: "lt",
    ratio: {
      stock_actual: 0.0,
      stock_minimo: 10.0,
      raw_ratio: 0.0,
      clamped_ratio: 0.0,
      status: "depleted",
    },
    is_depleted: true,
    bodega_color: "#10B981",
    bodega_icono: "snowflake",
    costo_promedio: 9200,
  },
  {
    producto_id: 103,
    bodega_id: 1,
    bodega_nombre: "Bodega Cocina Central",
    producto_nombre: "Harina de Trigo Especial",
    stock_actual: 12.0,
    stock_minimo: 20.0,
    unidad_medida: "kg",
    ratio: {
      stock_actual: 12.0,
      stock_minimo: 20.0,
      raw_ratio: 60.0,
      clamped_ratio: 60.0,
      status: "warning",
    },
    is_depleted: false,
    bodega_color: "#3B82F6",
    bodega_icono: "warehouse",
    costo_promedio: 1100,
  },
];

/**
 * Canonical test dataset for Expired Lots (lotes caducados con saldo físico).
 */
export const MOCK_EXPIRED_LOTS: readonly ExpiredLotAlert[] = [
  {
    producto_id: 201,
    bodega_id: 2,
    bodega_nombre: "Cámara Fría -18°C",
    producto_nombre: "Crema de Leche 35%",
    lote_codigo: "LOT-2026-CR01",
    fecha_vencimiento: "2026-10-18",
    cantidad_vencida: 8.0,
    dias_vencido: 7,
    costo_ppp: 3400,
    valor_total_riesgo: 27200,
    unidad_medida: "lt",
    bodega_color: "#10B981",
    bodega_icono: "snowflake",
  },
  {
    producto_id: 202,
    bodega_id: 1,
    bodega_nombre: "Bodega Cocina Central",
    producto_nombre: "Yogurt Natural Gastronómico",
    lote_codigo: "LOT-YG-991",
    fecha_vencimiento: "2026-10-22",
    cantidad_vencida: 5.0,
    dias_vencido: 3,
    costo_ppp: 2100,
    valor_total_riesgo: 10500,
    unidad_medida: "kg",
    bodega_color: "#3B82F6",
    bodega_icono: "warehouse",
  },
];

/**
 * Canonical test dataset for Upcoming Expiries (lotes por expirar ventana FEFO 30 días).
 */
export const MOCK_UPCOMING_EXPIRIES: readonly UpcomingExpiryAlert[] = [
  {
    producto_id: 301,
    bodega_id: 2,
    bodega_nombre: "Cámara Fría -18°C",
    producto_nombre: "Salmón Atlántico Fresco",
    lote_codigo: "LOT-SALM-04",
    fecha_vencimiento: "2026-10-28",
    cantidad_en_riesgo: 15.0,
    dias_restantes: 3,
    costo_ppp: 12500,
    valor_total_riesgo: 187500,
    unidad_medida: "kg",
    bodega_color: "#10B981",
    bodega_icono: "snowflake",
  },
  {
    producto_id: 302,
    bodega_id: 1,
    bodega_nombre: "Bodega Cocina Central",
    producto_nombre: "Queso Mozzarella Barra",
    lote_codigo: "LOT-MOZ-88",
    fecha_vencimiento: "2026-11-04",
    cantidad_en_riesgo: 10.0,
    dias_restantes: 10,
    costo_ppp: 6800,
    valor_total_riesgo: 68000,
    unidad_medida: "kg",
    bodega_color: "#3B82F6",
    bodega_icono: "warehouse",
  },
];

/**
 * Consolidated Mock Summary Response matching GET /api/v1/inventory/alerts.
 */
export const MOCK_ALERTS_SUMMARY: AlertsSummary = {
  total_count: 7,
  critical_count: 3,
  expired_count: 2,
  upcoming_count: 2,
  has_critical: true,
  total_financial_risk: 293200,
  critical_stock: MOCK_CRITICAL_STOCK,
  expired_lots: MOCK_EXPIRED_LOTS,
  upcoming_expiries: MOCK_UPCOMING_EXPIRIES,
};

/**
 * Lightweight Mock Badge Response matching GET /api/v1/inventory/alerts/badge.
 */
export const MOCK_ALERTS_BADGE: AlertBadge = {
  total_count: 7,
  has_critical: true,
  critical_stock_count: 3,
  expired_count: 2,
  upcoming_count: 2,
};

/**
 * Maps AlertsSummary into legacy-compatible `AlertProductItem[]` (`ProductoAnalitico`).
 */
export function mapSummaryToProductItems(summary: AlertsSummary): AlertProductItem[] {
  const items: AlertProductItem[] = [];

  // 1. Critical stock
  for (const c of summary.critical_stock) {
    items.push({
      id: `${c.producto_id}::${c.bodega_id}`,
      producto_id: c.producto_id,
      nombre: c.producto_nombre,
      unidad: c.unidad_medida,
      stock_minimo: c.stock_minimo,
      cantidad: c.stock_actual,
      cantidad_vencida: 0,
      fecha_vencimiento: null,
      bodega_id: c.bodega_id,
      bodega_nombre: c.bodega_nombre,
      bodega_color: c.bodega_color,
      bodega_icono: c.bodega_icono,
      costo_promedio: c.costo_promedio,
      costo_unitario: c.costo_promedio,
      alert_type: "critical",
      ratio: c.ratio,
      is_depleted: c.is_depleted,
    });
  }

  // 2. Expired lots
  for (const e of summary.expired_lots) {
    items.push({
      id: `${e.producto_id}::${e.bodega_id}::exp::${e.lote_codigo ?? "no-lot"}`,
      producto_id: e.producto_id,
      nombre: e.producto_nombre,
      unidad: e.unidad_medida,
      stock_minimo: 0,
      cantidad: e.cantidad_vencida,
      cantidad_vencida: e.cantidad_vencida,
      fecha_vencimiento: e.fecha_vencimiento,
      bodega_id: e.bodega_id,
      bodega_nombre: e.bodega_nombre,
      bodega_color: e.bodega_color,
      bodega_icono: e.bodega_icono,
      costo_promedio: e.costo_ppp,
      costo_unitario: e.costo_ppp,
      alert_type: "expired",
      lote_codigo: e.lote_codigo,
      dias_vencido: e.dias_vencido,
      valor_total_riesgo: e.valor_total_riesgo,
    });
  }

  // 3. Upcoming expiries
  for (const u of summary.upcoming_expiries) {
    items.push({
      id: `${u.producto_id}::${u.bodega_id}::upc::${u.lote_codigo ?? "no-lot"}`,
      producto_id: u.producto_id,
      nombre: u.producto_nombre,
      unidad: u.unidad_medida,
      stock_minimo: 0,
      cantidad: u.cantidad_en_riesgo,
      cantidad_vencida: 0,
      fecha_vencimiento: u.fecha_vencimiento,
      bodega_id: u.bodega_id,
      bodega_nombre: u.bodega_nombre,
      bodega_color: u.bodega_color,
      bodega_icono: u.bodega_icono,
      costo_promedio: u.costo_ppp,
      costo_unitario: u.costo_ppp,
      alert_type: "upcoming",
      lote_codigo: u.lote_codigo,
      dias_restantes: u.dias_restantes,
      valor_total_riesgo: u.valor_total_riesgo,
    });
  }

  return items;
}

export const MOCK_PRODUCTOS_ANALITICOS: readonly AlertProductItem[] =
  mapSummaryToProductItems(MOCK_ALERTS_SUMMARY);
