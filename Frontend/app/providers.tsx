"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { Toaster } from "@/components/ui/sonner";
import { apiErrorDetail } from "@/lib/api";

function mutationSuccessMessage(meta: unknown): string {
  if (typeof meta === "object" && meta !== null && "successMessage" in meta) {
    const message = (meta as { successMessage?: unknown }).successMessage;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }

  return "Action completed";
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(
    () =>
      new QueryClient({
        mutationCache: new MutationCache({
          onError: (error) => {
            toast.error(`Failed to save - ${apiErrorDetail(error)}`);
          },
          onSuccess: (_data, _variables, _context, mutation) => {
            if (mutation.options.meta?.suppressToast) {
              return;
            }

            toast.success(mutationSuccessMessage(mutation.options.meta));
          },
        }),
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            staleTime: 30000,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster />
    </QueryClientProvider>
  );
}
