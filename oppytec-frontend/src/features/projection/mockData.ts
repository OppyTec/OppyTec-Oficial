/**
 * oppytec-frontend/src/features/projection/mockData.ts
 * Datos de simulación deterministas y realistas para modo offline, fallback de tests y storybook.
 */
import type {
  DayPoint,
  EventProjectionAlert,
  PaginatedProjectionResponse,
  ProductCurveDetail,
  ProjectionMetricsSummary,
  ProjectionProductOverview,
  TransferSuggestion,
} from "./types";

export const MOCK_PROJECTION_PRODUCTS: readonly ProjectionProductOverview[] = [
  {
    id: "proj-1",
    producto_id: 101,
    nombre: "Pechuga de Pollo Deshuesada",
    sku: "CAR-POL-001",
    unidad: "kg",
    categoria_id: 1,
    categoria_nombre: "Carnes y Aves",
    bodega_id: 1,
    bodega_nombre: "Cocina Central",
    current_qty: 45.5,
    projected_qty: 0,
    stock_minimo: 15.0,
    costo_unitario: 5200,
    depletion_date: "2026-11-12",
    worst_status: "critical",
    worst_status_label: "Quiebre inminente (Día 11)",
    worst_day: 11,
    horizon_days: 30,
    daily_consumption_rate: 3.8,
    is_stale: false,
    calculated_at: "2026-11-01T12:00:00Z",
  },
  {
    id: "proj-2",
    producto_id: 102,
    nombre: "Crema de Leche 35% MG",
    sku: "LAC-CRE-002",
    unidad: "L",
    categoria_id: 2,
    categoria_nombre: "Lácteos y Huevos",
    bodega_id: 1,
    bodega_nombre: "Cocina Central",
    current_qty: 28.0,
    projected_qty: 4.2,
    stock_minimo: 8.0,
    costo_unitario: 3900,
    depletion_date: "2026-11-24",
    worst_status: "warning",
    worst_status_label: "Bajo stock mínimo (Día 23)",
    worst_day: 23,
    horizon_days: 30,
    daily_consumption_rate: 0.9,
    is_stale: false,
    calculated_at: "2026-11-01T12:00:00Z",
  },
  {
    id: "proj-3",
    producto_id: 103,
    nombre: "Salmón Fresco Filete",
    sku: "PES-SAL-003",
    unidad: "kg",
    categoria_id: 3,
    categoria_nombre: "Pescados y Mariscos",
    bodega_id: 1,
    bodega_nombre: "Cocina Central",
    current_qty: 18.0,
    projected_qty: 0,
    stock_minimo: 10.0,
    costo_unitario: 14500,
    depletion_date: "2026-11-08",
    worst_status: "critical",
    worst_status_label: "Sin stock por evento masivo (Día 7)",
    worst_day: 7,
    horizon_days: 30,
    daily_consumption_rate: 1.5,
    is_stale: false,
    calculated_at: "2026-11-01T12:00:00Z",
  },
  {
    id: "proj-4",
    producto_id: 104,
    nombre: "Lomo Liso Vacuno Angus",
    sku: "CAR-VAC-004",
    unidad: "kg",
    categoria_id: 1,
    categoria_nombre: "Carnes y Aves",
    bodega_id: 2,
    bodega_nombre: "Bodega Bar & Grill",
    current_qty: 62.0,
    projected_qty: 22.4,
    stock_minimo: 12.0,
    costo_unitario: 13800,
    depletion_date: null,
    worst_status: "normal",
    worst_status_label: "Stock saludable y estable",
    worst_day: null,
    horizon_days: 30,
    daily_consumption_rate: 1.32,
    is_stale: false,
    calculated_at: "2026-11-01T12:00:00Z",
  },
  {
    id: "proj-5",
    producto_id: 105,
    nombre: "Aceite de Oliva Extra Virgen 5L",
    sku: "ABA-ACE-005",
    unidad: "bidon",
    categoria_id: 4,
    categoria_nombre: "Abarrotes y Despensa",
    bodega_id: 1,
    bodega_nombre: "Cocina Central",
    current_qty: 14.0,
    projected_qty: 3.5,
    stock_minimo: 4.0,
    costo_unitario: 32000,
    depletion_date: "2026-11-28",
    worst_status: "warning",
    worst_status_label: "Lotes vencen día 27",
    worst_day: 27,
    horizon_days: 30,
    daily_consumption_rate: 0.35,
    is_stale: false,
    calculated_at: "2026-11-01T12:00:00Z",
  },
  {
    id: "proj-6",
    producto_id: 106,
    nombre: "Harina de Trigo Especial",
    sku: "ABA-HAR-006",
    unidad: "kg",
    categoria_id: 4,
    categoria_nombre: "Abarrotes y Despensa",
    bodega_id: 1,
    bodega_nombre: "Cocina Central",
    current_qty: 120.0,
    projected_qty: 75.0,
    stock_minimo: 30.0,
    costo_unitario: 980,
    depletion_date: null,
    worst_status: "normal",
    worst_status_label: "Stock suficiente",
    worst_day: null,
    horizon_days: 30,
    daily_consumption_rate: 1.5,
    is_stale: false,
    calculated_at: "2026-11-01T12:00:00Z",
  },
];

export const MOCK_PAGINATED_PROJECTION_RESPONSE: PaginatedProjectionResponse = {
  items: MOCK_PROJECTION_PRODUCTS,
  total_items: MOCK_PROJECTION_PRODUCTS.length,
  page: 1,
  page_size: 30,
  total_pages: 1,
  has_next: false,
  has_prev: false,
};

export function generateMockCurvePoints(
  currentStock: number,
  dailyRate: number,
  horizonDays: number = 30,
  minStock: number = 15
): DayPoint[] {
  const points: DayPoint[] = [];
  let remaining = currentStock;
  const baseDate = new Date("2026-11-01T00:00:00Z");

  for (let d = 0; d <= horizonDays; d++) {
    const pointDate = new Date(baseDate);
    pointDate.setDate(baseDate.getDate() + d);
    const isoDate = pointDate.toISOString().slice(0, 10);
    const label = `${pointDate.toLocaleDateString("es-CL", { weekday: "short" })} ${pointDate.getDate()}/${pointDate.getMonth() + 1}`;

    if (d > 0) {
      remaining = Math.max(0, Number((remaining - dailyRate).toFixed(2)));
    }

    // Inyectar evento el día 7
    let eventsDeduction = 0;
    const eventsList = [];
    if (d === 7) {
      eventsDeduction = 5.0;
      remaining = Math.max(0, Number((remaining - eventsDeduction).toFixed(2)));
      eventsList.push({
        id: "evt-banquete",
        name: "Cena Gala Médica (80 pax)",
        qty: 5.0,
        salon: "Salón Principal",
      });
    }

    // Inyectar caducidad el día 18
    let expiringQty = 0;
    const expiringList = [];
    if (d === 18 && remaining > 0) {
      expiringQty = 2.0;
      remaining = Math.max(0, Number((remaining - expiringQty).toFixed(2)));
      expiringList.push({
        lote_id: "lot-992",
        numero_lote: "L-202610-09",
        fecha_vencimiento: isoDate,
        cantidad: 2.0,
      });
    }

    let status: "normal" | "warning" | "critical" = "normal";
    let statusLabel = "Stock saludable";
    if (remaining <= 0) {
      status = "critical";
      statusLabel = "Sin stock disponible";
    } else if (remaining <= minStock) {
      status = "warning";
      statusLabel = "Por debajo del stock de seguridad";
    }

    points.push({
      date: isoDate,
      day_index: d,
      label,
      qty: remaining,
      status,
      statusLabel,
      expiring_qty: expiringQty,
      event_deduction: eventsDeduction,
      events: eventsList.length > 0 ? eventsList : undefined,
      expiring: expiringList.length > 0 ? expiringList : undefined,
    });
  }

  return points;
}

export const MOCK_PRODUCT_CURVE_DETAIL: ProductCurveDetail = {
  producto_id: 101,
  producto_nombre: "Pechuga de Pollo Deshuesada",
  bodega_id: 1,
  bodega_nombre: "Cocina Central",
  horizon_days: 30,
  current_stock: 45.5,
  projected_stock: 0,
  depletion_date: "2026-11-12",
  worst_status: "critical",
  worst_status_label: "Quiebre inminente (Día 11)",
  worst_day: 11,
  daily_consumption_rate: 3.8,
  curve: generateMockCurvePoints(45.5, 3.8, 30, 15),
};

export const MOCK_TRANSFER_SUGGESTIONS: readonly TransferSuggestion[] = [
  {
    producto_id: 101,
    bodega_origen_id: 2,
    bodega_origen_nombre: "Bodega Bar & Grill",
    bodega_destino_id: 1,
    cantidad_sugerida: 18.0,
    dias_cobertura_restante_origen: 16,
    urgencia: "critical",
  },
  {
    producto_id: 103,
    bodega_origen_id: 3,
    bodega_origen_nombre: "Cámara Congelados Puerto",
    bodega_destino_id: 1,
    cantidad_sugerida: 8.5,
    dias_cobertura_restante_origen: 22,
    urgencia: "critical",
  },
];

export const MOCK_PROJECTION_ALERTS: readonly EventProjectionAlert[] = [
  {
    producto_id: 101,
    producto_nombre: "Pechuga de Pollo Deshuesada",
    bodega_id: 1,
    bodega_nombre: "Cocina Central",
    status: "critical",
    status_label: "Agotamiento total día 11 (consumo continuo + evento)",
    depletion_date: "2026-11-12",
    worst_day: 11,
    current_stock: 45.5,
    projected_stock: 0,
    event_name: "Cena de Gala Corporativa Tech",
    event_date: "2026-11-12",
    required_qty: 60.0,
    deficit_qty: 14.5,
    transfer_suggestions: [MOCK_TRANSFER_SUGGESTIONS[0]!],
  },
  {
    producto_id: 103,
    producto_nombre: "Salmón Fresco Filete",
    bodega_id: 1,
    bodega_nombre: "Cocina Central",
    status: "critical",
    status_label: "Déficit por banquete corporativo en día 7",
    depletion_date: "2026-11-08",
    worst_day: 7,
    current_stock: 18.0,
    projected_stock: 0,
    event_name: "Matrimonio González-Larraín",
    event_date: "2026-11-08",
    required_qty: 25.0,
    deficit_qty: 7.0,
    transfer_suggestions: [MOCK_TRANSFER_SUGGESTIONS[1]!],
  },
];

export const MOCK_PROJECTION_METRICS_SUMMARY: ProjectionMetricsSummary = {
  total_items: 6,
  in_warning_count: 2,
  in_critical_count: 2,
  normal_count: 2,
  avg_coverage_days: 14.8,
  total_value_at_risk: 312500,
};
