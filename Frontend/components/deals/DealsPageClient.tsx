"use client";

import { useQuery } from "@tanstack/react-query";
import { LayoutGrid, List, Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DealForm } from "@/components/deals/DealForm";
import { ForecastChart } from "@/components/deals/ForecastChart";
import { KanbanBoard } from "@/components/deals/KanbanBoard";
import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn, formatCurrency, formatDate } from "@/lib/utils";
import { usePermissions } from "@/lib/permissions";
import type { Deal, DealForecastResponse, DealKanbanResponse, Pipeline } from "@/types/api";

type ViewMode = "kanban" | "list";

const PAGE_SIZE = 100;
const STORAGE_KEY = "doxa:last-pipeline-id";

function toNumber(value: number | string): number {
  return typeof value === "number" ? value : Number(value);
}

export function DealsPageClient() {
  const { canWriteDeals } = usePermissions();
  const [selectedPipelineId, setSelectedPipelineId] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("kanban");
  const [formOpen, setFormOpen] = useState(false);

  const pipelinesQuery = useQuery({
    queryFn: () => api.get<Pipeline[]>("/pipelines/"),
    queryKey: ["pipelines", "deals-page"],
  });
  const pipelines = pipelinesQuery.data ?? [];

  useEffect(() => {
    if (selectedPipelineId || pipelines.length === 0) {
      return;
    }

    const storedPipelineId = window.localStorage.getItem(STORAGE_KEY);
    const storedPipeline = pipelines.find((pipeline) => pipeline.id === storedPipelineId);
    const defaultPipeline = storedPipeline ?? pipelines.find((pipeline) => pipeline.is_default) ?? pipelines[0];
    setSelectedPipelineId(defaultPipeline.id);
  }, [pipelines, selectedPipelineId]);

  function selectPipeline(pipelineId: string) {
    setSelectedPipelineId(pipelineId);
    window.localStorage.setItem(STORAGE_KEY, pipelineId);
  }

  const kanbanQuery = useQuery({
    enabled: Boolean(selectedPipelineId),
    queryFn: () => api.get<DealKanbanResponse>("/deals/kanban", { page_size: PAGE_SIZE, pipeline_id: selectedPipelineId }),
    queryKey: ["deals", "kanban", selectedPipelineId],
  });
  const forecastQuery = useQuery({
    enabled: Boolean(selectedPipelineId),
    queryFn: () => api.get<DealForecastResponse>("/deals/forecast", { pipeline_id: selectedPipelineId }),
    queryKey: ["deals", "forecast", selectedPipelineId],
  });
  const dealsQuery = useQuery({
    enabled: Boolean(selectedPipelineId),
    queryFn: () => api.get<Deal[]>("/deals/", { page_size: PAGE_SIZE, pipeline_id: selectedPipelineId }),
    queryKey: ["deals", "list", selectedPipelineId],
  });

  const detailsById = useMemo(() => new Map((dealsQuery.data ?? []).map((deal) => [deal.id, deal])), [dealsQuery.data]);
  const selectedPipeline = pipelines.find((pipeline) => pipeline.id === selectedPipelineId);
  const listColumns = useMemo<Array<DataTableColumn<Deal>>>(
    () => [
      {
        cell: (deal) => (
          <Link className="font-semibold text-[#0F2444] hover:text-[#2563EB]" href={`/deals/${deal.id}`}>
            {deal.title}
          </Link>
        ),
        header: "Deal",
        id: "title",
      },
      { cell: (deal) => deal.account_name ?? deal.account_id.slice(0, 8), header: "Account", id: "account" },
      { cell: (deal) => deal.stage_name ?? deal.stage_id.slice(0, 8), header: "Stage", id: "stage" },
      { cell: (deal) => formatCurrency(toNumber(deal.value), deal.currency), header: "Value", id: "value" },
      { cell: (deal) => <StatusPill status={deal.status} type="deal" />, header: "Status", id: "status" },
      { cell: (deal) => formatDate(deal.expected_close), header: "Expected Close", id: "expected_close" },
      { cell: (deal) => deal.owner_name ?? deal.owner_id.slice(0, 8), header: "Owner", id: "owner" },
    ],
    [],
  );

  return (
    <div className="grid gap-6">
      <PageHeader
        primaryAction={canWriteDeals ? { icon: Plus, label: "New Deal", onClick: () => setFormOpen(true) } : undefined}
        subtitle="Manage pipeline stages, forecast, and opportunity movement."
        title="Sales Pipeline"
      />

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {pipelinesQuery.isLoading ? <Skeleton className="h-10 w-48" /> : null}
            {pipelines.map((pipeline) => (
              <button
                className={cn(
                  "rounded-md px-3 py-2 text-sm font-semibold transition-colors",
                  selectedPipelineId === pipeline.id ? "bg-[#2563EB] text-white" : "bg-[#EFF6FF] text-[#2563EB] hover:bg-blue-100",
                )}
                key={pipeline.id}
                onClick={() => selectPipeline(pipeline.id)}
                type="button"
              >
                {pipeline.name}
              </button>
            ))}
          </div>

          <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
            <button
              className={cn(
                "inline-flex items-center gap-2 rounded px-3 py-1.5 text-sm font-medium",
                viewMode === "kanban" ? "bg-white text-[#0F2444] shadow-sm" : "text-[#64748B]",
              )}
              onClick={() => setViewMode("kanban")}
              type="button"
            >
              <LayoutGrid className="h-4 w-4" aria-hidden="true" />
              Kanban
            </button>
            <button
              className={cn(
                "inline-flex items-center gap-2 rounded px-3 py-1.5 text-sm font-medium",
                viewMode === "list" ? "bg-white text-[#0F2444] shadow-sm" : "text-[#64748B]",
              )}
              onClick={() => setViewMode("list")}
              type="button"
            >
              <List className="h-4 w-4" aria-hidden="true" />
              List
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-xl bg-[#0F2444] p-5 text-white shadow-sm">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-white/70">{selectedPipeline?.name ?? "Pipeline"} Forecast</p>
          {forecastQuery.isLoading ? (
            <Skeleton className="h-8 w-80 bg-white/20" />
          ) : (
            <p className="text-xl font-bold">
              Weighted Forecast: {formatCurrency(forecastQuery.data?.total_weighted ?? 0)} | Total Open:{" "}
              {formatCurrency(forecastQuery.data?.total_open ?? 0)}
            </p>
          )}
        </div>
      </section>

      <ForecastChart pipelineId={selectedPipelineId} />

      {viewMode === "kanban" ? (
        kanbanQuery.isLoading ? (
          <Skeleton className="h-[680px] rounded-xl" />
        ) : kanbanQuery.isError ? (
          <div className="rounded-xl border border-red-100 bg-white p-5 text-sm text-red-700 shadow-sm">Could not load Kanban board.</div>
        ) : (
          <KanbanBoard canDrag={canWriteDeals} detailsById={detailsById} stages={kanbanQuery.data?.stages ?? []} />
        )
      ) : (
        <DataTable
          columns={listColumns}
          data={dealsQuery.data ?? []}
          emptyMessage="No deals found."
          getRowKey={(deal) => deal.id}
          isLoading={dealsQuery.isLoading}
        />
      )}

      {canWriteDeals ? <DealForm onOpenChange={setFormOpen} open={formOpen} selectedPipelineId={selectedPipelineId} /> : null}
    </div>
  );
}
