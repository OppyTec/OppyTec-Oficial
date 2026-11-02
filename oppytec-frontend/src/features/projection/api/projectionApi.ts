/**
 * oppytec-frontend/src/features/projection/api/projectionApi.ts
 * Capa de Cliente API REST para el Módulo de Proyección de Demanda, Curvas FEFO y Traspasos Preventivos.
 * Integra apiRequest centralizado con fallback automático offline y tipado estricto.
 */
import { apiRequest } from "@/shared/api/httpClient";
import {
  MOCK_PAGINATED_PROJECTION_RESPONSE,
  MOCK_PRODUCT_CURVE_DETAIL,
  MOCK_PROJECTION_ALERTS,
  MOCK_TRANSFER_SUGGESTIONS,
} from "../mockData";
import type {
  DayPoint,
  EventProjectionAlert,
  PaginatedProjectionResponse,
  ProductCurveDetail,
  ProjectionFilters,
  ProjectionProductOverview,
  ProjectionUrgencyStatus,
  RecomputeResponsePayload,
  TransferSuggestion,
} from "../types";

const BASE_PATH = "/api/v1/projection";

/**
 * Representación en bruto devuelta por el Backend FastAPI (donde Decimal se serializa como string).
 */
interface RawProjectionCardItem {
  readonly id: number | string;
  readonly producto_id: number | string;
  readonly producto_nombre: string;
  readonly producto_sku?: string;
  readonly categoria_id?: number | null;
  readonly categoria_nombre?: string | null;
  readonly bodega_id?: number | null;
  readonly bodega_nombre?: string | null;
  readonly horizon_days: number;
  readonly current_stock: string | number;
  readonly projected_stock: string | number;
  readonly stock_minimo?: string | number;
  readonly costo_unitario?: string | number;
  readonly depletion_date?: string | null;
  readonly worst_status: string;
  readonly worst_status_label: string;
  readonly worst_day?: number | null;
  readonly daily_consumption_rate?: string | number;
  readonly is_stale?: boolean;
  readonly calculated_at?: string | null;
  readonly unidad?: string;
}

interface RawPaginatedResponse {
  readonly items: readonly RawProjectionCardItem[];
  readonly total_items: number;
  readonly page: number;
  readonly page_size: number;
  readonly total_pages: number;
  readonly has_next: boolean;
  readonly has_prev: boolean;
}

interface RawDayPoint {
  readonly date: string;
  readonly day_index?: number;
  readonly qty: string | number;
  readonly status: string;
  readonly status_label?: string;
  readonly statusLabel?: string;
  readonly label?: string;
  readonly expiring_qty?: string | number;
  readonly event_deduction?: string | number;
  readonly events?: readonly { id?: string | number; name: string; qty: number; salon?: string }[];
  readonly expiring_lots?: readonly { lote_id?: string | number; numero_lote?: string; fecha_vencimiento: string; cantidad: number }[];
  readonly expiring?: readonly { lote_id?: string | number; numero_lote?: string; fecha_vencimiento: string; cantidad: number }[];
}

interface RawProductCurveDetail {
  readonly producto_id: number | string;
  readonly producto_nombre: string;
  readonly bodega_id?: number | null;
  readonly bodega_nombre?: string | null;
  readonly horizon_days: number;
  readonly current_stock: string | number;
  readonly projected_stock: string | number;
  readonly depletion_date?: string | null;
  readonly worst_status: string;
  readonly worst_status_label: string;
  readonly worst_day?: number | null;
  readonly daily_consumption_rate: string | number;
  readonly curve: readonly RawDayPoint[];
}

interface RawTransferRecommendation {
  readonly producto_id: number | string;
  readonly bodega_origen_id: number | string;
  readonly bodega_origen_nombre?: string | null;
  readonly bodega_destino_id: number | string;
  readonly cantidad_sugerida: string | number;
  readonly dias_cobertura_restante_origen: number;
  readonly urgencia: string;
}

interface RawProjectionAlert {
  readonly producto_id: number | string;
  readonly producto_nombre: string;
  readonly bodega_id?: number | null;
  readonly bodega_nombre?: string | null;
  readonly status: string;
  readonly status_label: string;
  readonly depletion_date?: string | null;
  readonly worst_day?: number | null;
  readonly current_stock: string | number;
  readonly projected_stock: string | number;
  readonly transfer_suggestions?: readonly RawTransferRecommendation[];
  readonly event_name?: string;
  readonly event_date?: string;
  readonly required_qty?: string | number;
  readonly deficit_qty?: string | number;
}

function parseUrgencyStatus(status: string): ProjectionUrgencyStatus {
  const normalized = status.toLowerCase();
  if (normalized === "critical") return "critical";
  if (normalized === "warning") return "warning";
  return "normal";
}

function normalizeCardItem(raw: RawProjectionCardItem): ProjectionProductOverview {
  return {
    id: raw.id,
    producto_id: raw.producto_id,
    nombre: raw.producto_nombre,
    sku: raw.producto_sku ?? "",
    unidad: raw.unidad ?? "un",
    categoria_id: raw.categoria_id ?? null,
    categoria_nombre: raw.categoria_nombre ?? null,
    bodega_id: raw.bodega_id ?? null,
    bodega_nombre: raw.bodega_nombre ?? null,
    current_qty: typeof raw.current_stock === "number" ? raw.current_stock : parseFloat(raw.current_stock || "0"),
    projected_qty: typeof raw.projected_stock === "number" ? raw.projected_stock : parseFloat(raw.projected_stock || "0"),
    stock_minimo: raw.stock_minimo !== undefined ? (typeof raw.stock_minimo === "number" ? raw.stock_minimo : parseFloat(String(raw.stock_minimo))) : 10,
    costo_unitario: raw.costo_unitario !== undefined ? (typeof raw.costo_unitario === "number" ? raw.costo_unitario : parseFloat(String(raw.costo_unitario))) : 0,
    depletion_date: raw.depletion_date ?? null,
    worst_status: parseUrgencyStatus(raw.worst_status),
    worst_status_label: raw.worst_status_label || "Normal",
    worst_day: raw.worst_day ?? null,
    horizon_days: raw.horizon_days,
    daily_consumption_rate: raw.daily_consumption_rate !== undefined ? (typeof raw.daily_consumption_rate === "number" ? raw.daily_consumption_rate : parseFloat(String(raw.daily_consumption_rate))) : 0,
    is_stale: Boolean(raw.is_stale),
    calculated_at: raw.calculated_at || new Date().toISOString(),
  };
}

function normalizeDayPoint(point: RawDayPoint, idx: number): DayPoint {
  const qty = typeof point.qty === "number" ? point.qty : parseFloat(String(point.qty || "0"));
  const expiringQty = point.expiring_qty !== undefined ? (typeof point.expiring_qty === "number" ? point.expiring_qty : parseFloat(String(point.expiring_qty || "0"))) : 0;
  const eventDeduction = point.event_deduction !== undefined ? (typeof point.event_deduction === "number" ? point.event_deduction : parseFloat(String(point.event_deduction || "0"))) : 0;

  return {
    date: point.date,
    day_index: point.day_index ?? idx,
    label: point.label || point.date.slice(5),
    qty,
    status: parseUrgencyStatus(point.status),
    statusLabel: point.statusLabel || point.status_label || point.status,
    expiring_qty: expiringQty,
    event_deduction: eventDeduction,
    events: point.events,
    expiring: point.expiring || point.expiring_lots,
  };
}

function normalizeTransferSuggestion(raw: RawTransferRecommendation): TransferSuggestion {
  return {
    producto_id: raw.producto_id,
    bodega_origen_id: raw.bodega_origen_id,
    bodega_origen_nombre: raw.bodega_origen_nombre ?? null,
    bodega_destino_id: raw.bodega_destino_id,
    cantidad_sugerida: typeof raw.cantidad_sugerida === "number" ? raw.cantidad_sugerida : parseFloat(String(raw.cantidad_sugerida || "0")),
    dias_cobertura_restante_origen: raw.dias_cobertura_restante_origen,
    urgencia: parseUrgencyStatus(raw.urgencia),
  };
}

export const projectionApi = {
  /**
   * Consulta server-side paginada de snapshots de proyección.
   */
  async getPaginatedSnapshots(filters: ProjectionFilters): Promise<PaginatedProjectionResponse> {
    const params = new URLSearchParams();
    params.set("page", String(filters.page));
    params.set("page_size", String(filters.pageSize));
    params.set("horizon_days", String(filters.horizonDays));

    if (filters.search && filters.search.trim().length > 0) {
      params.set("search", filters.search.trim());
    }
    if (filters.bodegaId !== undefined && filters.bodegaId !== "all") {
      params.set("bodega_id", String(filters.bodegaId));
    }
    if (filters.categoryId !== undefined && filters.categoryId !== "all") {
      params.set("category_id", String(filters.categoryId));
    }
    if (filters.status && filters.status !== "all") {
      params.set("status", filters.status);
    }
    if (filters.sortBy) {
      params.set("sort_by", filters.sortBy);
    }

    const endpoint = `${BASE_PATH}/snapshots?${params.toString()}`;
    const response = await apiRequest<RawPaginatedResponse>(endpoint, {
      method: "GET",
      fallbackData: {
        items: MOCK_PAGINATED_PROJECTION_RESPONSE.items.map((item) => ({
          id: item.id,
          producto_id: item.producto_id,
          producto_nombre: item.nombre,
          producto_sku: item.sku,
          categoria_id: item.categoria_id ? Number(item.categoria_id) : null,
          categoria_nombre: item.categoria_nombre,
          bodega_id: item.bodega_id ? Number(item.bodega_id) : null,
          bodega_nombre: item.bodega_nombre,
          horizon_days: item.horizon_days,
          current_stock: String(item.current_qty),
          projected_stock: String(item.projected_qty),
          stock_minimo: item.stock_minimo ? String(item.stock_minimo) : "10.0000",
          costo_unitario: item.costo_unitario ? String(item.costo_unitario) : "0",
          depletion_date: item.depletion_date,
          worst_status: item.worst_status,
          worst_status_label: item.worst_status_label,
          worst_day: item.worst_day,
          daily_consumption_rate: item.daily_consumption_rate ? String(item.daily_consumption_rate) : "0.0000",
          is_stale: item.is_stale,
          calculated_at: item.calculated_at,
          unidad: item.unidad,
        })),
        total_items: MOCK_PAGINATED_PROJECTION_RESPONSE.total_items,
        page: filters.page,
        page_size: filters.pageSize,
        total_pages: MOCK_PAGINATED_PROJECTION_RESPONSE.total_pages,
        has_next: MOCK_PAGINATED_PROJECTION_RESPONSE.has_next,
        has_prev: MOCK_PAGINATED_PROJECTION_RESPONSE.has_prev,
      },
    });

    const raw = response.data;
    return {
      items: raw.items.map(normalizeCardItem),
      total_items: raw.total_items,
      page: raw.page,
      page_size: raw.page_size,
      total_pages: raw.total_pages,
      has_next: raw.has_next,
      has_prev: raw.has_prev,
    };
  },

  /**
   * Obtiene la serie temporal día a día de un producto para graficar en Recharts.
   */
  async getProductCurve(
    productId: string | number,
    bodegaId?: string | number | "all",
    horizonDays: number = 30
  ): Promise<ProductCurveDetail> {
    const params = new URLSearchParams();
    params.set("horizon_days", String(horizonDays));
    if (bodegaId !== undefined && bodegaId !== "all") {
      params.set("bodega_id", String(bodegaId));
    }

    const endpoint = `${BASE_PATH}/products/${productId}/curve?${params.toString()}`;
    const response = await apiRequest<RawProductCurveDetail>(endpoint, {
      method: "GET",
      fallbackData: {
        producto_id: productId,
        producto_nombre: MOCK_PRODUCT_CURVE_DETAIL.producto_nombre,
        bodega_id: bodegaId !== undefined && bodegaId !== "all" ? Number(bodegaId) : 1,
        bodega_nombre: MOCK_PRODUCT_CURVE_DETAIL.bodega_nombre,
        horizon_days: horizonDays,
        current_stock: String(MOCK_PRODUCT_CURVE_DETAIL.current_stock),
        projected_stock: String(MOCK_PRODUCT_CURVE_DETAIL.projected_stock),
        depletion_date: MOCK_PRODUCT_CURVE_DETAIL.depletion_date,
        worst_status: MOCK_PRODUCT_CURVE_DETAIL.worst_status,
        worst_status_label: MOCK_PRODUCT_CURVE_DETAIL.worst_status_label,
        worst_day: MOCK_PRODUCT_CURVE_DETAIL.worst_day,
        daily_consumption_rate: String(MOCK_PRODUCT_CURVE_DETAIL.daily_consumption_rate),
        curve: MOCK_PRODUCT_CURVE_DETAIL.curve.map((p) => ({
          date: p.date,
          day_index: p.day_index,
          qty: String(p.qty),
          status: p.status,
          status_label: p.statusLabel,
          expiring_qty: p.expiring_qty ? String(p.expiring_qty) : "0",
          event_deduction: p.event_deduction ? String(p.event_deduction) : "0",
          events: p.events,
          expiring: p.expiring,
        })),
      },
    });

    const raw = response.data;
    return {
      producto_id: raw.producto_id,
      producto_nombre: raw.producto_nombre,
      bodega_id: raw.bodega_id,
      bodega_nombre: raw.bodega_nombre,
      horizon_days: raw.horizon_days,
      current_stock: typeof raw.current_stock === "number" ? raw.current_stock : parseFloat(raw.current_stock || "0"),
      projected_stock: typeof raw.projected_stock === "number" ? raw.projected_stock : parseFloat(raw.projected_stock || "0"),
      depletion_date: raw.depletion_date ?? null,
      worst_status: parseUrgencyStatus(raw.worst_status),
      worst_status_label: raw.worst_status_label,
      worst_day: raw.worst_day ?? null,
      daily_consumption_rate: typeof raw.daily_consumption_rate === "number" ? raw.daily_consumption_rate : parseFloat(String(raw.daily_consumption_rate || "0")),
      curve: raw.curve.map(normalizeDayPoint),
    };
  },

  /**
   * Obtiene la consola de alertas de quiebre y riesgos de stock futuros.
   */
  async getProjectionAlerts(
    bodegaId?: string | number | "all",
    horizonDays: number = 30
  ): Promise<EventProjectionAlert[]> {
    const params = new URLSearchParams();
    params.set("horizon_days", String(horizonDays));
    if (bodegaId !== undefined && bodegaId !== "all") {
      params.set("bodega_id", String(bodegaId));
    }

    const endpoint = `${BASE_PATH}/alerts?${params.toString()}`;
    const response = await apiRequest<readonly RawProjectionAlert[]>(endpoint, {
      method: "GET",
      fallbackData: MOCK_PROJECTION_ALERTS.map((al) => ({
        producto_id: al.producto_id,
        producto_nombre: al.producto_nombre,
        bodega_id: al.bodega_id ? Number(al.bodega_id) : null,
        bodega_nombre: al.bodega_nombre,
        status: al.status,
        status_label: al.status_label,
        depletion_date: al.depletion_date,
        worst_day: al.worst_day,
        current_stock: String(al.current_stock),
        projected_stock: String(al.projected_stock),
        event_name: al.event_name,
        event_date: al.event_date,
        required_qty: al.required_qty !== undefined ? String(al.required_qty) : undefined,
        deficit_qty: al.deficit_qty !== undefined ? String(al.deficit_qty) : undefined,
        transfer_suggestions: al.transfer_suggestions.map((ts) => ({
          producto_id: ts.producto_id,
          bodega_origen_id: ts.bodega_origen_id,
          bodega_origen_nombre: ts.bodega_origen_nombre,
          bodega_destino_id: ts.bodega_destino_id,
          cantidad_sugerida: String(ts.cantidad_sugerida),
          dias_cobertura_restante_origen: ts.dias_cobertura_restante_origen,
          urgencia: ts.urgencia,
        })),
      })),
    });

    return response.data.map((raw) => ({
      producto_id: raw.producto_id,
      producto_nombre: raw.producto_nombre,
      bodega_id: raw.bodega_id ?? null,
      bodega_nombre: raw.bodega_nombre ?? null,
      status: parseUrgencyStatus(raw.status),
      status_label: raw.status_label,
      depletion_date: raw.depletion_date ?? null,
      worst_day: raw.worst_day ?? null,
      current_stock: typeof raw.current_stock === "number" ? raw.current_stock : parseFloat(raw.current_stock || "0"),
      projected_stock: typeof raw.projected_stock === "number" ? raw.projected_stock : parseFloat(raw.projected_stock || "0"),
      event_name: raw.event_name,
      event_date: raw.event_date,
      required_qty: raw.required_qty !== undefined ? (typeof raw.required_qty === "number" ? raw.required_qty : parseFloat(String(raw.required_qty))) : undefined,
      deficit_qty: raw.deficit_qty !== undefined ? (typeof raw.deficit_qty === "number" ? raw.deficit_qty : parseFloat(String(raw.deficit_qty))) : undefined,
      transfer_suggestions: (raw.transfer_suggestions ?? []).map(normalizeTransferSuggestion),
    }));
  },

  /**
   * Forzar recálculo masivo del motor de proyección en el tenant.
   */
  async recomputeSnapshots(horizonDays: number = 30): Promise<RecomputeResponsePayload> {
    const startTime = performance.now();
    const response = await apiRequest<RecomputeResponsePayload>(`${BASE_PATH}/recompute`, {
      method: "POST",
      body: { horizon_days: horizonDays },
      fallbackData: {
        status: "completed",
        processed: 45,
        horizon_days: horizonDays,
        message: "Recálculo completado exitosamente",
      },
    });

    const elapsed = Math.round(performance.now() - startTime);
    return {
      ...response.data,
      duration_ms: response.data.duration_ms ?? elapsed,
    };
  },

  /**
   * Sugerencias de traspaso específicas para un producto en quiebre.
   */
  async getTransferSuggestions(
    productId: string | number,
    bodegaId: string | number,
    neededQty: number = 10,
    dateNeeded?: string
  ): Promise<TransferSuggestion[]> {
    const params = new URLSearchParams();
    params.set("bodega_id", String(bodegaId));
    params.set("needed_qty", String(neededQty));
    if (dateNeeded) {
      params.set("date_needed", dateNeeded);
    }

    const endpoint = `${BASE_PATH}/products/${productId}/transfer-suggestions?${params.toString()}`;
    const response = await apiRequest<readonly RawTransferRecommendation[]>(endpoint, {
      method: "GET",
      fallbackData: MOCK_TRANSFER_SUGGESTIONS.map((ts) => ({
        producto_id: ts.producto_id,
        bodega_origen_id: ts.bodega_origen_id,
        bodega_origen_nombre: ts.bodega_origen_nombre,
        bodega_destino_id: ts.bodega_destino_id,
        cantidad_sugerida: String(ts.cantidad_sugerida),
        dias_cobertura_restante_origen: ts.dias_cobertura_restante_origen,
        urgencia: ts.urgencia,
      })),
    });

    return response.data.map(normalizeTransferSuggestion);
  },
};
