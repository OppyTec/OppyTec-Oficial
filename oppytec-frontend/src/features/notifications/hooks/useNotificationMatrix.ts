import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import {
  type CargoMatrixItem,
  MOCK_NOTIFICATION_MATRIX,
  type NotificationCatalogItem,
  type NotificationMatrixData,
  type NotificationMatrixRule,
} from "../types";

export interface UseNotificationMatrixReturn {
  readonly data: NotificationMatrixData;
  readonly catalog: readonly NotificationCatalogItem[];
  readonly cargos: readonly CargoMatrixItem[];
  readonly rules: readonly NotificationMatrixRule[];
  readonly isAdmin: boolean;
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  readonly updateMatrix: (
    rules: readonly NotificationMatrixRule[]
  ) => Promise<NotificationMatrixData>;
  readonly updateCargoPermissions: (
    cargoId: number,
    permissions: Record<string, boolean>
  ) => Promise<unknown>;
  readonly isUpdating: boolean;
}

export function useNotificationMatrix(): UseNotificationMatrixReturn {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "default";

  const queryKey = useMemo(
    () => queryKeys.approvals.matrix(tenantId),
    [tenantId]
  );

  const {
    data: rawData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<NotificationMatrixData>({
    queryKey,
    queryFn: async () => {
      const endpoint = "/api/v1/operations/solicitudes/matrix";
      const res = await apiRequest<NotificationMatrixData>(endpoint, {
        method: "GET",
        fallbackData: MOCK_NOTIFICATION_MATRIX,
      });
      return res.data;
    },
    staleTime: 60_000,
  });

  const matrixData = rawData ?? MOCK_NOTIFICATION_MATRIX;

  // Mutación para actualizar la matriz masivamente
  const updateMatrixMutation = useMutation({
    mutationFn: async (rules: readonly NotificationMatrixRule[]) => {
      const endpoint = "/api/v1/operations/solicitudes/matrix";
      const res = await apiRequest<NotificationMatrixData>(endpoint, {
        method: "PUT",
        body: { rules: [...rules] },
      });
      return res.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKey, updated);
      void queryClient.invalidateQueries({ queryKey });
      toast.success("Matriz de gobernanza guardada exitosamente");
    },
    onError: (err: any) => {
      const msg =
        err?.message ||
        "Error al guardar la matriz de gobernanza. Intente nuevamente.";
      toast.error(msg);
    },
  });

  // Mutación para actualizar permisos por cargo individual
  const updateCargoMutation = useMutation({
    mutationFn: async ({
      cargoId,
      permissions,
    }: {
      cargoId: number;
      permissions: Record<string, boolean>;
    }) => {
      const endpoint = `/api/v1/operations/solicitudes/matrix/cargo/${cargoId}`;
      const res = await apiRequest<{ status: string; cargo_id: number }>(
        endpoint,
        {
          method: "PUT",
          body: { notification_permissions: permissions },
        }
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
      toast.success("Permisos del cargo actualizados");
    },
    onError: (err: any) => {
      const msg =
        err?.message ||
        "Error al actualizar permisos del cargo.";
      toast.error(msg);
    },
  });

  const updateMatrix = useCallback(
    async (
      rules: readonly NotificationMatrixRule[]
    ): Promise<NotificationMatrixData> => {
      return updateMatrixMutation.mutateAsync(rules);
    },
    [updateMatrixMutation]
  );

  const updateCargoPermissions = useCallback(
    async (
      cargoId: number,
      permissions: Record<string, boolean>
    ): Promise<unknown> => {
      return updateCargoMutation.mutateAsync({ cargoId, permissions });
    },
    [updateCargoMutation]
  );

  return {
    data: matrixData,
    catalog: matrixData.catalog,
    cargos: matrixData.cargos,
    rules: matrixData.rules,
    isAdmin: matrixData.is_admin,
    isLoading,
    isError,
    error,
    refetch,
    updateMatrix,
    updateCargoPermissions,
    isUpdating:
      updateMatrixMutation.isPending || updateCargoMutation.isPending,
  };
}
