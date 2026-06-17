"use client";

import { useQuery } from "@tanstack/react-query";
import { RefreshCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ApiErrorPayload, LeadFunnelResponse } from "@/types/api";

const DASHBOARD_REFETCH_INTERVAL = 300000;

interface FunnelRow {
  fill: string;
  stage: string;
  total: number;
}

interface FunnelTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: FunnelRow }>;
}

function getErrorMessage(error: unknown): string {
  const apiError = error as Partial<ApiErrorPayload>;
  return typeof apiError.detail === "string" ? apiError.detail : "Could not load lead funnel.";
}

function formatPercent(value: number): string {
  return `${Math.round(value * 10) / 10}%`;
}

function FunnelTooltip({ active, payload }: FunnelTooltipProps) {
  const item = payload?.[0]?.payload;

  if (!active || !item) {
    return null;
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs shadow-sm">
      <p className="font-semibold text-[#0F2444]">{item.stage}</p>
      <p className="mt-1 text-[#64748B]">{item.total.toLocaleString()} records</p>
    </div>
  );
}

export function LeadFunnelChart() {
  const [chartReady, setChartReady] = useState(false);
  const { data, error, isError, isLoading, isFetching, refetch } = useQuery({
    queryFn: () => api.get<LeadFunnelResponse>("/reports/lead-funnel"),
    queryKey: ["dashboard", "lead-funnel"],
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  });

  useEffect(() => {
    setChartReady(true);
  }, []);

  const chartData = useMemo<FunnelRow[]>(
    () =>
      data
        ? [
            { fill: "#2563EB", stage: "Leads", total: data.total_leads },
            { fill: "#60A5FA", stage: "Qualified", total: data.qualified_leads },
            { fill: "#1D4ED8", stage: "Won", total: data.won_deals },
          ]
        : [],
    [data],
  );

  return (
    <section className="rounded-xl bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-[#0F2444]">Lead Funnel</h2>
          <p className="mt-1 text-sm text-[#64748B]">Leads to qualified opportunities to won deals.</p>
        </div>
        {isError ? (
          <button
            className="inline-flex items-center gap-2 rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
            onClick={() => void refetch()}
            type="button"
          >
            <RefreshCcw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} aria-hidden="true" />
            Retry
          </button>
        ) : null}
      </div>

      <div className="mt-5 h-[280px]">
        {isLoading ? (
          <Skeleton className="h-full w-full rounded-xl" />
        ) : isError || !data ? (
          <div className="flex h-full items-center rounded-xl border border-red-100 bg-red-50/50 p-4 text-sm text-red-700">
            {getErrorMessage(error)}
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-[#64748B]">
            No lead funnel data yet.
          </div>
        ) : chartReady ? (
          <ResponsiveContainer height="100%" width="100%">
            <BarChart data={chartData} layout="vertical" margin={{ bottom: 8, left: 0, right: 20, top: 8 }}>
              <CartesianGrid stroke="#E2E8F0" horizontal={false} />
              <XAxis axisLine={false} fontSize={12} tick={{ fill: "#64748B" }} tickLine={false} type="number" />
              <YAxis
                axisLine={false}
                dataKey="stage"
                fontSize={12}
                tick={{ fill: "#64748B" }}
                tickLine={false}
                type="category"
                width={82}
              />
              <Tooltip content={<FunnelTooltip />} cursor={{ fill: "#EFF6FF" }} />
              <Bar dataKey="total" radius={[0, 8, 8, 0]}>
                {chartData.map((entry) => (
                  <Cell fill={entry.fill} key={entry.stage} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <Skeleton className="h-full w-full rounded-xl" />
        )}
      </div>

      {!isLoading && data ? (
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-lg bg-[#EFF6FF] p-3">
            <p className="text-xs font-medium text-[#64748B]">Lead to Qualified</p>
            <p className="mt-1 text-lg font-bold text-[#0F2444]">{formatPercent(data.qualification_rate)}</p>
          </div>
          <div className="rounded-lg bg-[#EFF6FF] p-3">
            <p className="text-xs font-medium text-[#64748B]">Lead to Converted</p>
            <p className="mt-1 text-lg font-bold text-[#0F2444]">{formatPercent(data.conversion_rate)}</p>
          </div>
          <div className="rounded-lg bg-[#EFF6FF] p-3">
            <p className="text-xs font-medium text-[#64748B]">Qualified to Won</p>
            <p className="mt-1 text-lg font-bold text-[#0F2444]">{formatPercent(data.win_rate)}</p>
          </div>
        </div>
      ) : null}
    </section>
  );
}
