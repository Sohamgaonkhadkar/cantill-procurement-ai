import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./http";
export const useOverview = () =>
  useQuery({ queryKey: ["overview"], queryFn: api.overview });
export const useMasters = () =>
  useQuery({ queryKey: ["masters"], queryFn: api.masters });
export const usePolicies = () =>
  useQuery({ queryKey: ["policies"], queryFn: api.policies });
export const useRuns = (offset = 0) =>
  useQuery({ queryKey: ["runs", offset], queryFn: () => api.runs(offset) });
export const useRequests = (
  filters: Record<string, string | number | undefined> = {},
) =>
  useQuery({
    queryKey: ["requirements", filters],
    queryFn: () => api.requirements(filters),
  });
export function useAction<T, V>(fn: (value: V) => Promise<T>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void qc.invalidateQueries();
    },
  });
}
