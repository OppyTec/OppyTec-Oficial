import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/httpClient";
import type { Collaborator } from "../types";
import { MOCK_COLLABORATORS } from "../mockData";

export function useCollaborators() {
  const query = useQuery({
    queryKey: ["oppytec", "collaborators"],
    queryFn: async (): Promise<Collaborator[]> => {
      const res = await apiRequest<Collaborator[]>("/api/v1/auth/users", {
        fallbackData: MOCK_COLLABORATORS,
      });
      return res.data;
    },
    staleTime: 1000 * 60 * 10,
  });

  return {
    collaborators: query.data ?? MOCK_COLLABORATORS,
    isLoading: query.isLoading,
  };
}
