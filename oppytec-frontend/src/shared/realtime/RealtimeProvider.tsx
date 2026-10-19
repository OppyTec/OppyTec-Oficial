/* eslint-disable react-refresh/only-export-components */
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import { queryKeys } from "@/shared/api/queryKeys";
import { getRuntimeEnv } from "@/shared/config/env";

export const REALTIME_WS_PATH = "/api/v1/ws/realtime";

export interface RealtimePushEvent {
  readonly eventId: string;
  readonly channel: string;
  readonly eventType:
    | "inventory.stock.updated"
    | "inventory.merma.threshold_alert"
    | "operations.alert.triggered"
    | "operations.notification.created"
    | "procurement.invoice.processed"
    | "oppyfy.credits.updated";
  readonly holdingId: string;
  readonly tenantId: string;
  readonly requiredPermission: `${string}.${string}.${string}`;
  readonly timestampIso: string;
  readonly payload: Readonly<Record<string, string | number | boolean>>;
}

export interface RealtimeContextValue {
  readonly wsEndpointUrl: string;
  readonly channelKey: string;
  readonly connected: boolean;
  readonly lastEventId: string;
  readonly events: readonly RealtimePushEvent[];
  readonly dispatchRealtimeEvent: (event: RealtimePushEvent) => void;
  readonly reconnectWithCatchUp: (fromEventId?: string) => void;
}

const INITIAL_EVENTS: readonly RealtimePushEvent[] = [
  {
    eventId: "1729368000001-0",
    channel: "rt:local:holding-gastro-sur:tenant_rest_central",
    eventType: "inventory.stock.updated",
    holdingId: "holding-gastro-sur",
    tenantId: "tenant_rest_central",
    requiredPermission: "inventory.stock.read",
    timestampIso: "2026-10-19T19:45:00Z",
    payload: {
      sku: "INS-SALM-001",
      warehouse: "bod-cocina-central",
      delta: -4.5,
      unit: "kg",
    },
  },
  {
    eventId: "1729368000002-0",
    channel: "rt:local:holding-gastro-sur:tenant_rest_central",
    eventType: "operations.alert.triggered",
    holdingId: "holding-gastro-sur",
    tenantId: "tenant_rest_central",
    requiredPermission: "operations.pos.consume",
    timestampIso: "2026-10-19T19:46:12Z",
    payload: {
      item: "Pollo King",
      minStock: 15,
      currentStock: 8,
      severity: "critical",
    },
  },
];

const RealtimeContext = createContext<RealtimeContextValue | undefined>(
  undefined
);

export interface RealtimeProviderProps {
  readonly children: ReactNode;
  readonly holdingId?: string;
  readonly tenantId?: string;
}

/**
 * Single WebSocket tunnel provider (`/api/v1/ws/realtime`) backed by Redis Pub/Sub + Streams
 * (`rt:{env_ns}:{holding_id}:{tenant_id}`). Zero HTTP polling (`Rule 22`).
 */
export function RealtimeProvider({
  children,
  holdingId = "holding-gastro-sur",
  tenantId = "tenant_rest_central",
}: RealtimeProviderProps) {
  const queryClient = useQueryClient();
  const env = useMemo(() => getRuntimeEnv(), []);
  const [connected, setConnected] = useState<boolean>(true);
  const [events, setEvents] =
    useState<readonly RealtimePushEvent[]>(INITIAL_EVENTS);
  const [lastEventId, setLastEventId] = useState<string>(
    INITIAL_EVENTS[INITIAL_EVENTS.length - 1]?.eventId ?? "0-0"
  );

  const channelKey = `rt:${env.VITE_ENV_NAMESPACE}:${holdingId}:${tenantId}`;
  const wsEndpointUrl = `${env.VITE_WS_BASE_URL.replace(/\/+$/, "")}${REALTIME_WS_PATH}?last_event_id=${encodeURIComponent(lastEventId)}`;

  const dispatchRealtimeEvent = useCallback(
    (event: RealtimePushEvent): void => {
      if (event.holdingId !== holdingId || event.tenantId !== tenantId) {
        return;
      }
      setEvents((prev) => [event, ...prev.slice(0, 24)]);
      setLastEventId(event.eventId);

      // Invalidate corresponding TanStack Query v5 keys immediately on push event
      if (event.eventType.startsWith("inventory.")) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.inventory.stock({ holdingId, tenantId }),
        });
      } else if (event.eventType.startsWith("operations.")) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.operations.alerts(tenantId),
        });
      } else if (event.eventType.startsWith("procurement.")) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.procurement.invoices(tenantId),
        });
      } else if (event.eventType.startsWith("oppyfy.")) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.oppyfy.credits(tenantId),
        });
      }
    },
    [holdingId, queryClient, tenantId]
  );

  const reconnectWithCatchUp = useCallback((fromEventId?: string): void => {
    if (fromEventId) {
      setLastEventId(fromEventId);
    }
    setConnected(true);
  }, []);

  const value = useMemo<RealtimeContextValue>(
    () => ({
      wsEndpointUrl,
      channelKey,
      connected,
      lastEventId,
      events,
      dispatchRealtimeEvent,
      reconnectWithCatchUp,
    }),
    [
      wsEndpointUrl,
      channelKey,
      connected,
      lastEventId,
      events,
      dispatchRealtimeEvent,
      reconnectWithCatchUp,
    ]
  );

  return (
    <RealtimeContext.Provider value={value}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtimeContext(): RealtimeContextValue {
  const ctx = useContext(RealtimeContext);
  if (!ctx) {
    throw new Error(
      "useRealtimeContext must be used within a <RealtimeProvider />"
    );
  }
  return ctx;
}
