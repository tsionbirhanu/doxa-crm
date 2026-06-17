"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { GlobalSearchResponse } from "@/types/api";

export function useGlobalSearch(q: string) {
  const query = q.trim();

  return useQuery({
    enabled: query.length >= 2,
    queryFn: () => api.get<GlobalSearchResponse>("/search/global", { limit: 20, q: query }),
    queryKey: ["search", "global", query],
    staleTime: 0,
  });
}
