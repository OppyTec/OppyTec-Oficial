import {
  type UseRealtimeSyncReturn,
  useRealtimeSync,
} from "@/shared/realtime/useRealtimeSync";

export function useWebSocket(): UseRealtimeSyncReturn {
  return useRealtimeSync();
}
