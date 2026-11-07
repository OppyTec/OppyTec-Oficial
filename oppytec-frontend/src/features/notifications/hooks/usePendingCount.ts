import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { isMockDataEnabled, MOCK_DATA_MODE_EVENT_NAME, useMockDataMode } from "@/shared/mock/mockModeStorage";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { MOCK_PENDING_COUNTS, type PendingCounts } from "../types";

const CLEAN_PENDING_COUNTS: PendingCounts = {
  total: 0,
  operaciones: 0,
  inventario: 0,
  compras: 0,
  equipo: 0,
  by_area: {},
};

export interface UsePendingCountOptions {
  readonly areaId?: string | number | null;
  readonly enabled?: boolean;
}

export interface UsePendingCountReturn {
  readonly counts: PendingCounts;
  readonly total: number;
  readonly operaciones: number;
  readonly inventario: number;
  readonly compras: number;
  readonly equipo: number;
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
}

interface RawPendingCountResponse {
  readonly total_pending: number;
  readonly by_category: {
    readonly operaciones?: number;
    readonly inventario?: number;
    readonly compras?: number;
    readonly equipo?: number;
  };
  readonly area_id?: string | null;
}

export function usePendingCount(
  options: UsePendingCountOptions = {}
): UsePendingCountReturn {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "default";
  const { isDemo } = useMockDataMode();

  const { areaId = "all", enabled = true } = options;

  const areaIdParam =
    areaId !== "all" && areaId !== null && areaId !== undefined
      ? String(areaId)
      : undefined;

  // Suscripción WebSocket Zero-Polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] =
    [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Desacoplado o en test
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "notification.created" ||
      lastEvent?.eventType === "notification.resolved" ||
      lastEvent?.eventType === "operations.notification.created" ||
      lastEvent?.eventType === "operations.notification.resolved" ||
      lastEvent?.eventType.startsWith("notification.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "approvals", "pendingCount"],
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener para sincronización local
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "approvals", "pendingCount"],
      });
    };
    window.addEventListener("approvals_changed", handleSync);
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleSync);
    return () => {
      window.removeEventListener("approvals_changed", handleSync);
      window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleSync);
    };
  }, [queryClient]);

  const queryKey = useMemo(
    () =>
      queryKeys.approvals.pendingCount({
        tenantId,
        areaId: areaIdParam ?? "all",
      }),
    [tenantId, areaIdParam]
  );

  const { data, isLoading, isError, error, refetch } =
    useQuery<PendingCounts>({
      queryKey,
      queryFn: async () => {
        const params = new URLSearchParams();
        if (areaIdParam) {
          params.append("area_id", areaIdParam);
        }
        const qs = params.toString();
        const endpoint = `/api/v1/operations/solicitudes/pending-count${qs ? `?${qs}` : ""}`;

        const activeMockCounts = isMockDataEnabled()
          ? MOCK_PENDING_COUNTS
          : CLEAN_PENDING_COUNTS;

        const fallbackPayload: RawPendingCountResponse = {
          total_pending: activeMockCounts.total,
          by_category: {
            operaciones: activeMockCounts.operaciones,
            inventario: activeMockCounts.inventario,
            compras: activeMockCounts.compras,
            equipo: activeMockCounts.equipo,
          },
          area_id: areaIdParam ?? null,
        };

        const res = await apiRequest<RawPendingCountResponse>(endpoint, {
          method: "GET",
          fallbackData: fallbackPayload,
        });

        const raw = res.data;
        return {
          total: raw.total_pending ?? 0,
          operaciones: raw.by_category?.operaciones ?? 0,
          inventario: raw.by_category?.inventario ?? 0,
          compras: raw.by_category?.compras ?? 0,
          equipo: raw.by_category?.equipo ?? 0,
          by_area: activeMockCounts.by_area,
        };
      },
      staleTime: 15_000,
      enabled,
    });

  const counts = data ?? (isDemo ? MOCK_PENDING_COUNTS : CLEAN_PENDING_COUNTS);

  return {
    counts,
    total: counts.total,
    operaciones: counts.operaciones,
    inventario: counts.inventario,
    compras: counts.compras,
    equipo: counts.equipo,
    isLoading,
    isError,
    error,
    refetch,
  };
}
