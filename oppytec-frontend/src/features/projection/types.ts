/**
 * oppytec-frontend/src/features/projection/types.ts
 * Contratos TypeScript de Dominio para el Módulo de Proyección de Demanda, Curvas FEFO y Traspasos Preventivos.
 * Estricto TypeScript 5, 0 any, 0 hardcoded strings.
 */

export type ProjectionUrgencyStatus = "normal" | "warning" | "critical";

export type ProjectionHorizonDays = 7 | 15 | 30 | 60 | 90;

export type ProjectionSortOrder =
  | "urgency_desc"
  | "name_asc"
  | "name_desc"
  | "projected_asc"
  | "current_desc";

export interface ProjectionEventDeductionItem {
  readonly id?: string | number;
  readonly name: string;
  readonly qty: number;
  readonly salon?: string;
  readonly date?: string;
}

export interface ProjectionExpiringLotItem {
  readonly lote_id?: string | number;
  readonly numero_lote?: string;
  readonly fecha_vencimiento: string;
  readonly cantidad: number;
}

export interface DayPoint {
  readonly date: string;
  readonly day_index?: number;
  readonly label: string;
  readonly qty: number;
  readonly status: ProjectionUrgencyStatus;
  readonly statusLabel: string;
  readonly expiring_qty?: number;
  readonly event_deduction?: number;
  readonly events?: readonly ProjectionEventDeductionItem[];
  readonly expiring?: readonly ProjectionExpiringLotItem[];
}

export interface TransferSuggestion {
  readonly producto_id: string | number;
  readonly bodega_origen_id: string | number;
  readonly bodega_origen_nombre?: string | null;
  readonly bodega_destino_id: string | number;
  readonly cantidad_sugerida: number;
  readonly dias_cobertura_restante_origen: number;
  readonly urgencia: ProjectionUrgencyStatus;
}

export interface ProjectionProductOverview {
  readonly id: string | number;
  readonly producto_id: string | number;
  readonly nombre: string;
  readonly sku?: string;
  readonly unidad?: string;
  readonly categoria_id?: string | number | null;
  readonly categoria_nombre?: string | null;
  readonly bodega_id?: string | number | null;
  readonly bodega_nombre?: string | null;
  readonly current_qty: number;
  readonly projected_qty: number;
  readonly stock_minimo?: number;
  readonly costo_unitario?: number;
  readonly depletion_date?: string | null;
  readonly worst_status: ProjectionUrgencyStatus;
  readonly worst_status_label: string;
  readonly worst_day?: number | null;
  readonly horizon_days: number;
  readonly daily_consumption_rate?: number;
  readonly is_stale?: boolean;
  readonly calculated_at: string;
}

export interface PaginatedProjectionResponse {
  readonly items: readonly ProjectionProductOverview[];
  readonly total_items: number;
  readonly page: number;
  readonly page_size: number;
  readonly total_pages: number;
  readonly has_next: boolean;
  readonly has_prev: boolean;
}

export interface ProductCurveDetail {
  readonly producto_id: string | number;
  readonly producto_nombre: string;
  readonly bodega_id?: string | number | null;
  readonly bodega_nombre?: string | null;
  readonly horizon_days: number;
  readonly current_stock: number;
  readonly projected_stock: number;
  readonly depletion_date?: string | null;
  readonly worst_status: ProjectionUrgencyStatus;
  readonly worst_status_label: string;
  readonly worst_day?: number | null;
  readonly daily_consumption_rate: number;
  readonly curve: readonly DayPoint[];
}

export interface EventProjectionAlert {
  readonly producto_id: string | number;
  readonly producto_nombre: string;
  readonly bodega_id?: string | number | null;
  readonly bodega_nombre?: string | null;
  readonly status: ProjectionUrgencyStatus;
  readonly status_label: string;
  readonly depletion_date?: string | null;
  readonly worst_day?: number | null;
  readonly current_stock: number;
  readonly projected_stock: number;
  readonly transfer_suggestions: readonly TransferSuggestion[];
  readonly event_name?: string;
  readonly event_date?: string;
  readonly required_qty?: number;
  readonly deficit_qty?: number;
}

export interface ProjectionFilters {
  readonly search?: string;
  readonly bodegaId?: string | number | "all";
  readonly categoryId?: string | number | "all";
  readonly status?: "all" | ProjectionUrgencyStatus;
  readonly sortBy?: ProjectionSortOrder;
  readonly horizonDays: number;
  readonly page: number;
  readonly pageSize: number;
}

export interface ProjectionMetricsSummary {
  readonly total_items: number;
  readonly in_warning_count: number;
  readonly in_critical_count: number;
  readonly normal_count: number;
  readonly avg_coverage_days: number;
  readonly total_value_at_risk?: number;
}

export interface RecomputeResponsePayload {
  readonly status: string;
  readonly processed: number;
  readonly horizon_days?: number;
  readonly duration_ms?: number;
  readonly message?: string;
}
