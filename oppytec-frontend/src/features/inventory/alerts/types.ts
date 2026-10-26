// oppytec-frontend/src/features/inventory/alerts/types.ts
/**
 * TypeScript Contracts for Inventory Alerts Module (/alertas).
 * Strict types matching backend Pydantic v2 schemas:
 * - CriticalStockAlertResponse
 * - ExpiredLotAlertResponse
 * - UpcomingExpiryAlertResponse
 * - AlertsSummaryResponse
 * - AlertsBadgeResponse
 * Preserves 100% semantic compatibility with historical ProductoAnalitico from OppyTec-Legacy.
 */

export interface StockHealthRatio {
  readonly stock_actual: number;
  readonly stock_minimo: number;
  readonly raw_ratio: number;
  readonly clamped_ratio: number;
  readonly status: "depleted" | "critical" | "warning" | "healthy";
}

export interface CriticalStockAlert {
  readonly producto_id: number;
  readonly bodega_id: number;
  readonly bodega_nombre: string;
  readonly producto_nombre: string;
  readonly stock_actual: number;
  readonly stock_minimo: number;
  readonly unidad_medida: string;
  readonly ratio: StockHealthRatio;
  readonly is_depleted: boolean;
  readonly bodega_color: string;
  readonly bodega_icono: string;
  readonly costo_promedio: number;
}

export interface ExpiredLotAlert {
  readonly producto_id: number;
  readonly bodega_id: number;
  readonly bodega_nombre: string;
  readonly producto_nombre: string;
  readonly lote_codigo: string | null;
  readonly fecha_vencimiento: string;
  readonly cantidad_vencida: number;
  readonly dias_vencido: number;
  readonly costo_ppp: number;
  readonly valor_total_riesgo: number;
  readonly unidad_medida: string;
  readonly bodega_color: string;
  readonly bodega_icono: string;
}

export interface UpcomingExpiryAlert {
  readonly producto_id: number;
  readonly bodega_id: number;
  readonly bodega_nombre: string;
  readonly producto_nombre: string;
  readonly lote_codigo: string | null;
  readonly fecha_vencimiento: string;
  readonly cantidad_en_riesgo: number;
  readonly dias_restantes: number;
  readonly costo_ppp: number;
  readonly valor_total_riesgo: number;
  readonly unidad_medida: string;
  readonly bodega_color: string;
  readonly bodega_icono: string;
}

export interface AlertsSummary {
  readonly total_count: number;
  readonly critical_count: number;
  readonly expired_count: number;
  readonly upcoming_count: number;
  readonly has_critical: boolean;
  readonly total_financial_risk: number;
  readonly critical_stock: readonly CriticalStockAlert[];
  readonly expired_lots: readonly ExpiredLotAlert[];
  readonly upcoming_expiries: readonly UpcomingExpiryAlert[];
}

export interface AlertBadge {
  readonly total_count: number;
  readonly has_critical: boolean;
  readonly critical_stock_count: number;
  readonly expired_count: number;
  readonly upcoming_count: number;
}

export type AlertFilterType = "all" | "stock" | "upcoming" | "expired";

export type AlertViewMode = "cards" | "list";

export interface CartPurchaseItem {
  readonly producto_id: number;
  readonly bodega_id: number;
  readonly bodega_nombre: string;
  readonly nombre: string;
  readonly cantidad: number;
  readonly precio: number;
  readonly unidad: string;
}

/**
 * Historical semantic compatibility model matching `ProductoAnalitico` from OppyTec-Legacy.
 * Enables unified rendering of cards, tables, and stock health indicators.
 */
export interface AlertProductItem {
  readonly id: string; // `${producto_id}::${bodega_id}` or `${producto_id}::${bodega_id}::${alert_type}::${lote_codigo}`
  readonly producto_id: number;
  readonly nombre: string;
  readonly unidad: string;
  readonly stock_minimo: number;
  readonly cantidad: number;
  readonly cantidad_vencida: number;
  readonly fecha_vencimiento: string | null;
  readonly bodega_id: number;
  readonly bodega_nombre: string;
  readonly bodega_color?: string;
  readonly bodega_icono?: string;
  readonly costo_promedio?: number;
  readonly costo_unitario?: number;
  // Extended analytics metadata
  readonly alert_type?: "critical" | "warning" | "expired" | "upcoming";
  readonly ratio?: StockHealthRatio;
  readonly is_depleted?: boolean;
  readonly lote_codigo?: string | null;
  readonly dias_vencido?: number;
  readonly dias_restantes?: number;
  readonly valor_total_riesgo?: number;
}

export type ProductoAnalitico = AlertProductItem;

export interface SmartNotification {
  readonly type: "critical" | "warning" | "info";
  readonly title: string;
  readonly key: string;
  readonly details: readonly { text: string; bodega?: string }[];
}
