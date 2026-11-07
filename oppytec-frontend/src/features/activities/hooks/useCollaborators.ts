import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/httpClient";
import { isMockDataEnabled, MOCK_DATA_MODE_EVENT_NAME } from "@/shared/mock/mockModeStorage";
import type { Collaborator } from "../types";
import { MOCK_COLLABORATORS } from "../mockData";

export function useCollaborators() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const handleMockModeChange = () => {
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "collaborators"] });
    };
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
    return () => window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
  }, [queryClient]);

  const query = useQuery({
    queryKey: ["oppytec", "collaborators"],
    queryFn: async (): Promise<Collaborator[]> => {
      const res = await apiRequest<Collaborator[]>("/api/v1/auth/users", {
        fallbackData: isMockDataEnabled() ? MOCK_COLLABORATORS : [],
      });
      return res.data;
    },
    staleTime: 1000 * 60 * 10,
  });

  return {
    collaborators: query.data ?? (isMockDataEnabled() ? MOCK_COLLABORATORS : []),
    isLoading: query.isLoading,
  };
}
