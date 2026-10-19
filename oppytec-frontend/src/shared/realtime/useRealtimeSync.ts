import { useMemo } from "react";
import { usePermissions } from "@/shared/auth/usePermissions";
import {
  type RealtimeContextValue,
  type RealtimePushEvent,
  useRealtimeContext,
} from "./RealtimeProvider";

export interface UseRealtimeSyncReturn extends RealtimeContextValue {
  readonly authorizedEvents: readonly RealtimePushEvent[];
}

/**
 * Synchronizes the single WebSocket tunnel (`/api/v1/ws/realtime`) with client-side
 * 3-level RBAC filtering and TanStack Query v5 cache invalidation. Zero HTTP polling.
 */
export function useRealtimeSync(): UseRealtimeSyncReturn {
  const realtime = useRealtimeContext();
  const { can } = usePermissions();

  const authorizedEvents = useMemo(
    () =>
      realtime.events.filter((evt) => can(evt.requiredPermission)),
    [can, realtime.events]
  );

  return {
    ...realtime,
    authorizedEvents,
  };
}
