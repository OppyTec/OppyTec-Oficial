// oppytec-frontend/src/features/inventory/hooks/useRecuentos.ts
import { useState, useMemo, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import type {
  PhysicalCountSession,
  PhysicalCountState,
} from "../types";
import { MOCK_PHYSICAL_COUNT_SESSIONS, MOCK_BODEGAS } from "../mockData";

export interface UseRecuentosOptions {
  initialBodegaId?: number | "all";
  initialStatus?: PhysicalCountState | "ALL";
}

export function useRecuentos(options?: UseRecuentosOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const [bodegaFilter, setBodegaFilter] = useState<number | "all">(
    options?.initialBodegaId ?? "all"
  );
  const [statusFilter, setStatusFilter] = useState<PhysicalCountState | "ALL">(
    options?.initialStatus ?? "ALL"
  );
  const [search, setSearch] = useState<string>("");
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);

  const queryKey = useMemo(
    () =>
      [
        "oppytec",
        "inventory",
        "counts",
        tenantId,
        String(bodegaFilter),
        statusFilter,
      ] as const,
    [tenantId, bodegaFilter, statusFilter]
  );

  const {
    data: sessionsData,
    isLoading,
    isError,
    refetch,
  } = useQuery<PhysicalCountSession[]>({
    queryKey,
    queryFn: async () => {
      let endpoint = "/api/v1/inventory/counts";
      const params = new URLSearchParams();
      if (bodegaFilter !== "all") {
        params.append("bodega_id", String(bodegaFilter));
      }
      if (statusFilter !== "ALL") {
        params.append("estado", statusFilter);
      }
      const queryString = params.toString();
      if (queryString) {
        endpoint += `?${queryString}`;
      }

      const res = await apiRequest<PhysicalCountSession[]>(endpoint, {
        method: "GET",
        fallbackData: MOCK_PHYSICAL_COUNT_SESSIONS,
      });

      if (Array.isArray(res.data) && res.data.length > 0) {
        return res.data.map((s) => {
          const bodega = MOCK_BODEGAS.find((b) => b.id === s.bodega_id);
          return {
            ...s,
            bodega_nombre: s.bodega_nombre || bodega?.nombre || `Bodega #${s.bodega_id}`,
            items: (s.items || []).map((item) => ({
              ...item,
              has_discrepancy:
                item.has_discrepancy ??
                Math.abs(item.stock_fisico_contado - item.stock_teorico_sistema) > 0.0001,
              is_surplus:
                item.is_surplus ??
                item.stock_fisico_contado > item.stock_teorico_sistema,
              is_shortage:
                item.is_shortage ??
                item.stock_fisico_contado < item.stock_teorico_sistema,
            })),
          };
        });
      }

      return MOCK_PHYSICAL_COUNT_SESSIONS;
    },
    staleTime: 60_000,
  });

  const rawSessions = useMemo(
    () => sessionsData ?? MOCK_PHYSICAL_COUNT_SESSIONS,
    [sessionsData]
  );

  // Filtrado de sesiones
  const filteredSessions = useMemo(() => {
    let result = [...rawSessions];

    if (search.trim()) {
      const q = search.toLowerCase().trim();
      result = result.filter(
        (s) =>
          s.bodega_nombre.toLowerCase().includes(q) ||
          s.responsable_nombre.toLowerCase().includes(q) ||
          (s.notas && s.notas.toLowerCase().includes(q)) ||
          s.items.some((i) => i.producto_nombre.toLowerCase().includes(q))
      );
    }

    if (bodegaFilter !== "all") {
      result = result.filter((s) => s.bodega_id === Number(bodegaFilter));
    }

    if (statusFilter !== "ALL") {
      result = result.filter((s) => s.estado === statusFilter);
    }

    // Orden cronológico descendente
    result.sort(
      (a, b) =>
        new Date(b.fecha_inicio).getTime() - new Date(a.fecha_inicio).getTime()
    );

    return result;
  }, [rawSessions, search, bodegaFilter, statusFilter]);

  const selectedSession = useMemo(() => {
    if (!selectedSessionId) return null;
    return rawSessions.find((s) => s.id === selectedSessionId) ?? null;
  }, [rawSessions, selectedSessionId]);

  // Aprobación de sesión física con impacto automático en Kardex
  const approveSession = useCallback(
    async (sessionId: number) => {
      try {
        const res = await apiRequest<PhysicalCountSession>(
          `/api/v1/inventory/counts/${sessionId}/approve`,
          {
            method: "POST",
          }
        );

        toast.success(
          `Acta #${sessionId} aprobada. Saldo conciliado en Kardex exitosamente.`
        );

        // Invalida tanto el listado de recuentos como el stock consolidado para sincronización instantánea
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory", "counts"] }),
          queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory", "stock"] }),
        ]);

        window.dispatchEvent(new CustomEvent("inventory_stock_updated"));
        return res.data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`Error al aprobar sesión: ${msg}`);
        throw err;
      }
    },
    [queryClient]
  );

  // Rechazo de sesión con orden de reconteo
  const rejectSession = useCallback(
    async (sessionId: number) => {
      try {
        const res = await apiRequest<PhysicalCountSession>(
          `/api/v1/inventory/counts/${sessionId}/reject`,
          {
            method: "POST",
          }
        );

        toast.info(`Acta #${sessionId} rechazada. Requiere reconteo físico.`);
        void queryClient.invalidateQueries({
          queryKey: ["oppytec", "inventory", "counts"],
        });
        return res.data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`Error al rechazar sesión: ${msg}`);
        throw err;
      }
    },
    [queryClient]
  );

  // Eliminación de sesión errónea (solo Propietario)
  const deleteSession = useCallback(
    async (sessionId: number) => {
      try {
        await apiRequest(`/api/v1/inventory/counts/${sessionId}`, {
          method: "DELETE",
        });

        toast.success(`Sesión #${sessionId} eliminada correctamente`);
        if (selectedSessionId === sessionId) {
          setSelectedSessionId(null);
        }
        void queryClient.invalidateQueries({
          queryKey: ["oppytec", "inventory", "counts"],
        });
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`Error al eliminar sesión: ${msg}`);
        throw err;
      }
    },
    [queryClient, selectedSessionId]
  );

  return {
    sessions: filteredSessions,
    allSessions: rawSessions,
    selectedSession,
    selectedSessionId,
    setSelectedSessionId,
    isLoading,
    isError,
    refetch,
    bodegaFilter,
    setBodegaFilter,
    statusFilter,
    setStatusFilter,
    search,
    setSearch,
    approveSession,
    rejectSession,
    deleteSession,
  };
}
