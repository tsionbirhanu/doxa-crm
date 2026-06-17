"use client";

import { RefreshCcw } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ReportCardProps {
  actions?: ReactNode;
  children: ReactNode;
  description?: string;
  empty?: boolean;
  error?: boolean;
  isFetching?: boolean;
  isLoading?: boolean;
  noDataText?: string;
  onRetry?: () => void;
  skeletonClassName?: string;
  title: string;
}

export function ReportCard({
  actions,
  children,
  description,
  empty,
  error,
  isFetching,
  isLoading,
  noDataText = "No data for this period.",
  onRetry,
  skeletonClassName = "h-[280px]",
  title,
}: ReportCardProps) {
  return (
    <section className="rounded-xl bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#0F2444]">{title}</h2>
          {description ? <p className="mt-1 text-sm text-[#64748B]">{description}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {actions}
          {error && onRetry ? (
            <Button onClick={onRetry} size="sm" type="button" variant="outline">
              <RefreshCcw className={cn("h-4 w-4", isFetching && "animate-spin")} aria-hidden="true" />
              Retry
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-5">
        {isLoading ? <Skeleton className={cn("w-full rounded-xl", skeletonClassName)} /> : null}
        {!isLoading && error ? (
          <div className={cn("flex items-center rounded-xl border border-red-100 bg-red-50/50 p-4 text-sm text-red-700", skeletonClassName)}>
            Could not load this report.
          </div>
        ) : null}
        {!isLoading && !error && empty ? (
          <div className={cn("flex items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-[#64748B]", skeletonClassName)}>
            {noDataText}
          </div>
        ) : null}
        {!isLoading && !error && !empty ? children : null}
      </div>
    </section>
  );
}
