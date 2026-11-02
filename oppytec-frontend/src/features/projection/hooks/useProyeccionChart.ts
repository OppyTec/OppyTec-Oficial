/**
 * oppytec-frontend/src/features/projection/hooks/useProyeccionChart.ts
 * Hook especializado para alimentar gráficos interactivos de Recharts (AreaChart / LineChart).
 * Realiza cálculos estadísticos de mínimos/máximos del eje Y, detección de quiebres FEFO,
 * consolidación de eventos y simulación rápida client-side.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { projectionApi } from "../api/projectionApi";
import type {
  DayPoint,
  ProductCurveDetail,
  ProjectionEventDeductionItem,
  ProjectionExpiringLotItem,
} from "../types";

export interface ChartCalculatedMetrics {
  readonly minQty: number;
  readonly maxQty: number;
  readonly yAxisDomain: readonly [number, number];
  readonly criticalPoint: DayPoint | null;
  readonly warningPoint: DayPoint | null;
  readonly eventsInHorizon: readonly ProjectionEventDeductionItem[];
  readonly expiringLotsInHorizon: readonly ProjectionExpiringLotItem[];
  readonly daysUntilDepletion: number | null;
}

/**
 * Simulación client-side ágil para pre-visualizaciones en tiempo real sin latencia de red.
 */
export function buildClientSimulatedChartData(
  currentStock: number,
  dailyRate: number,
  horizonDays: number = 30,
  minStock: number = 10,
  events: readonly ProjectionEventDeductionItem[] = [],
  expiringLots: readonly ProjectionExpiringLotItem[] = []
): DayPoint[] {
  const points: DayPoint[] = [];
  let remaining = currentStock;
  const today = new Date();

  // Mapear eventos por fecha
  const eventsByDate = new Map<string, ProjectionEventDeductionItem[]>();
  for (const ev of events) {
    if (ev.date) {
      const existing = eventsByDate.get(ev.date) ?? [];
      existing.push(ev);
      eventsByDate.set(ev.date, existing);
    }
  }

  // Mapear vencimientos por fecha
  const expiringByDate = new Map<string, ProjectionExpiringLotItem[]>();
  for (const lot of expiringLots) {
    const existing = expiringByDate.get(lot.fecha_vencimiento) ?? [];
    existing.push(lot);
    expiringByDate.set(lot.fecha_vencimiento, existing);
  }

  for (let d = 0; d <= horizonDays; d++) {
    const curDate = new Date(today);
    curDate.setDate(today.getDate() + d);
    const isoDate = curDate.toISOString().slice(0, 10);
    const weekday = curDate.toLocaleDateString("es-CL", { weekday: "short" });
    const label = `${weekday} ${curDate.getDate()}/${curDate.getMonth() + 1}`;

    if (d > 0) {
      remaining = Math.max(0, Number((remaining - dailyRate).toFixed(2)));
    }

    const dayEvents = eventsByDate.get(isoDate) ?? [];
    const eventDeduction = dayEvents.reduce((acc, ev) => acc + (ev.qty ?? 0), 0);
    if (eventDeduction > 0) {
      remaining = Math.max(0, Number((remaining - eventDeduction).toFixed(2)));
    }

    const dayLots = expiringByDate.get(isoDate) ?? [];
    const expiringQty = dayLots.reduce((acc, lot) => acc + (lot.cantidad ?? 0), 0);
    if (expiringQty > 0) {
      remaining = Math.max(0, Number((remaining - expiringQty).toFixed(2)));
    }

    let status: "normal" | "warning" | "critical" = "normal";
    let statusLabel = "Stock saludable";
    if (remaining <= 0) {
      status = "critical";
      statusLabel = "Sin stock proyectado";
    } else if (remaining <= minStock) {
      status = "warning";
      statusLabel = "Por debajo de stock mínimo";
    }

    points.push({
      date: isoDate,
      day_index: d,
      label,
      qty: remaining,
      status,
      statusLabel,
      expiring_qty: expiringQty > 0 ? expiringQty : undefined,
      event_deduction: eventDeduction > 0 ? eventDeduction : undefined,
      events: dayEvents.length > 0 ? dayEvents : undefined,
      expiring: dayLots.length > 0 ? dayLots : undefined,
    });
  }

  return points;
}

export function useProyeccionChart(
  productId: string | number | null,
  bodegaId?: string | number | "all",
  horizonDays: number = 30
) {
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const curveQuery = useQuery<ProductCurveDetail, Error>({
    queryKey: queryKeys.projection.curve(
      tenantId,
      productId ?? "none",
      bodegaId ?? "all",
      horizonDays
    ),
    queryFn: () => {
      if (!productId) {
        throw new Error("Se requiere un producto_id para consultar la curva");
      }
      return projectionApi.getProductCurve(productId, bodegaId, horizonDays);
    },
    enabled: Boolean(productId),
    staleTime: 1000 * 60 * 5, // 5 minutos
  });

  const curvePoints = useMemo(() => {
    return curveQuery.data?.curve ?? [];
  }, [curveQuery.data?.curve]);

  const metrics = useMemo<ChartCalculatedMetrics>(() => {
    if (curvePoints.length === 0) {
      return {
        minQty: 0,
        maxQty: 100,
        yAxisDomain: [0, 100],
        criticalPoint: null,
        warningPoint: null,
        eventsInHorizon: [],
        expiringLotsInHorizon: [],
        daysUntilDepletion: null,
      };
    }

    let min = Infinity;
    let max = -Infinity;
    let firstCritical: DayPoint | null = null;
    let firstWarning: DayPoint | null = null;
    const allEvents: ProjectionEventDeductionItem[] = [];
    const allExpiring: ProjectionExpiringLotItem[] = [];

    for (const pt of curvePoints) {
      if (pt.qty < min) min = pt.qty;
      if (pt.qty > max) max = pt.qty;

      if (!firstCritical && pt.status === "critical") {
        firstCritical = pt;
      }
      if (!firstWarning && (pt.status === "warning" || pt.status === "critical")) {
        firstWarning = pt;
      }

      if (pt.events && pt.events.length > 0) {
        allEvents.push(...pt.events);
      }
      if (pt.expiring && pt.expiring.length > 0) {
        allExpiring.push(...pt.expiring);
      }
    }

    const safeMin = Math.max(0, Math.floor(min));
    // Añadimos 15% de margen superior para que los tooltips y curvas respiren visualmente
    const safeMax = Math.max(10, Math.ceil(max * 1.15));

    const daysUntilDepletion = firstCritical?.day_index ?? (curveQuery.data?.worst_day ?? null);

    return {
      minQty: safeMin,
      maxQty: safeMax,
      yAxisDomain: [0, safeMax],
      criticalPoint: firstCritical,
      warningPoint: firstWarning,
      eventsInHorizon: allEvents,
      expiringLotsInHorizon: allExpiring,
      daysUntilDepletion,
    };
  }, [curvePoints, curveQuery.data?.worst_day]);

  return {
    detail: curveQuery.data,
    curvePoints,
    metrics,
    isLoading: curveQuery.isLoading,
    isFetching: curveQuery.isFetching,
    isError: curveQuery.isError,
    error: curveQuery.error,
    refetch: curveQuery.refetch,
  };
}
