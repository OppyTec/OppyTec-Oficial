/**
 * oppytec-frontend/src/features/oppyfy/hooks/useOppyfyRbac.ts
 * Hook reactivo para el sistema RBAC propio y editable de OppyFy (v2.0):
 * - Consulta del árbol de dominios/subdominios (`GET /api/v1/oppyfy/rbac/domains`)
 * - Creación y actualización de dominios (`POST /api/v1/oppyfy/rbac/domains`)
 * - Otorgamiento de permisos temporales (`POST /api/v1/oppyfy/rbac/grants`)
 *   con validación de triple caducidad: expires_at, max_prompts, temp_credit_ceiling.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import type {
  OppyfyDomainTreeResponse,
  OppyfyDomainCreateRequest,
  OppyfyGrantCreateRequest,
  OppyfyGrantResponse,
} from "../types";

export interface UseOppyfyRbacOptions {
  readonly tenantId?: string;
}

export function useOppyfyRbac(options?: UseOppyfyRbacOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = options?.tenantId ?? context.tenantId;

  // 1. Árbol de dominios y subdominios de OppyFy
  const domainsQuery = useQuery({
    queryKey: queryKeys.oppyfy.rbacDomains(tenantId),
    queryFn: async (): Promise<OppyfyDomainTreeResponse[]> => {
      const response = await apiRequest<OppyfyDomainTreeResponse[]>(
        "/api/v1/oppyfy/rbac/domains"
      );
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutos
  });

  // 2. Creación / Actualización de dominio con subdominios
  const createDomainMutation = useMutation({
    mutationFn: async (
      payload: OppyfyDomainCreateRequest
    ): Promise<OppyfyDomainTreeResponse> => {
      const response = await apiRequest<OppyfyDomainTreeResponse>(
        "/api/v1/oppyfy/rbac/domains",
        {
          method: "POST",
          body: payload,
        }
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.rbacDomains(tenantId),
      });
    },
  });

  // 3. Otorgamiento de permiso temporal con triple caducidad
  const createGrantMutation = useMutation({
    mutationFn: async (
      payload: OppyfyGrantCreateRequest
    ): Promise<OppyfyGrantResponse> => {
      // Validación previa de triple caducidad
      if (payload.max_prompts !== undefined && payload.max_prompts !== null) {
        if (payload.max_prompts <= 0) {
          throw new Error("El límite de consultas (max_prompts) debe ser mayor a 0.");
        }
      }

      if (
        payload.temp_credit_ceiling !== undefined &&
        payload.temp_credit_ceiling !== null
      ) {
        const ceilingNum = Number(payload.temp_credit_ceiling);
        if (isNaN(ceilingNum) || ceilingNum < 0) {
          throw new Error("El tope de créditos temporales debe ser un número no negativo.");
        }
      }

      if (payload.expires_at) {
        const expDate = new Date(payload.expires_at);
        if (isNaN(expDate.getTime())) {
          throw new Error("La fecha de expiración proporcionada no es válida.");
        }
      }

      const response = await apiRequest<OppyfyGrantResponse>(
        "/api/v1/oppyfy/rbac/grants",
        {
          method: "POST",
          body: payload,
        }
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.rbacDomains(tenantId),
      });
    },
  });

  return {
    domains: domainsQuery.data ?? [],
    isLoadingDomains: domainsQuery.isLoading,
    isErrorDomains: domainsQuery.isError,
    domainsError: domainsQuery.error,
    refetchDomains: domainsQuery.refetch,

    createDomain: createDomainMutation.mutateAsync,
    isCreatingDomain: createDomainMutation.isPending,
    createDomainError: createDomainMutation.error,

    createGrant: createGrantMutation.mutateAsync,
    isCreatingGrant: createGrantMutation.isPending,
    createGrantError: createGrantMutation.error,
  };
}
