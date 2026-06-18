"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { differenceInCalendarDays } from "date-fns";
import { Check, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { usePermissions } from "@/lib/permissions";
import { cn } from "@/lib/utils";
import type { ApiErrorPayload, Task } from "@/types/api";

const DASHBOARD_REFETCH_INTERVAL = 300000;

function getErrorMessage(error: unknown): string {
  const apiError = error as Partial<ApiErrorPayload>;
  return typeof apiError.detail === "string" ? apiError.detail : "Could not load overdue tasks.";
}

function shortId(id?: string | null): string {
  return id ? id.slice(0, 8) : "Unassigned";
}

function linkedEntityLabel(task: Task): string {
  if (task.contact_id) {
    return `Contact ${shortId(task.contact_id)}`;
  }

  if (task.deal_id) {
    return `Deal ${shortId(task.deal_id)}`;
  }

  if (task.lead_id) {
    return `Lead ${shortId(task.lead_id)}`;
  }

  if (task.account_id) {
    return `Account ${shortId(task.account_id)}`;
  }

  return "No linked record";
}

function getDaysOverdue(task: Task): number {
  if (!task.due_at) {
    return 0;
  }

  return Math.max(0, differenceInCalendarDays(new Date(), new Date(task.due_at)));
}

function OverdueTasksSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((item) => (
        <div className="rounded-lg border border-slate-100 p-3" key={item}>
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-2">
              <Skeleton className="h-4 w-44" />
              <Skeleton className="h-3 w-28" />
            </div>
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function OverdueTasksList() {
  const queryClient = useQueryClient();
  const { canWriteTasks } = usePermissions();
  const tasksQuery = useQuery({
    queryFn: () => api.get<Task[]>("/tasks/overdue", { page_size: 5 }),
    queryKey: ["dashboard", "overdue-tasks"],
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  });
  const completeTask = useMutation({
    mutationFn: (id: string) => api.post<Task>(`/tasks/${id}/complete`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["reports", "dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks", "overdue"] });
    },
  });

  const tasks = (tasksQuery.data ?? []).slice(0, 5);

  return (
    <section className="rounded-xl bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-[#0F2444]">Overdue Tasks</h2>
          <p className="mt-1 text-sm text-[#64748B]">The oldest overdue work that needs attention.</p>
        </div>
        {tasksQuery.isError ? (
          <button
            className="inline-flex items-center gap-2 rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
            onClick={() => void tasksQuery.refetch()}
            type="button"
          >
            <RefreshCcw className={cn("h-3.5 w-3.5", tasksQuery.isFetching && "animate-spin")} aria-hidden="true" />
            Retry
          </button>
        ) : null}
      </div>

      <div className="mt-5">
        {tasksQuery.isLoading ? (
          <OverdueTasksSkeleton />
        ) : tasksQuery.isError ? (
          <div className="rounded-xl border border-red-100 bg-red-50/50 p-4 text-sm text-red-700">
            {getErrorMessage(tasksQuery.error)}
          </div>
        ) : tasks.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-[#64748B]">
            No overdue tasks — you're on top of it.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {tasks.map((task) => {
              const daysOverdue = getDaysOverdue(task);

              return (
                <div className="grid gap-3 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center" key={task.id}>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-[#0F2444]">{task.title}</p>
                      <span className="rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-600">
                        {daysOverdue}d overdue
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-[#64748B]">
                      {linkedEntityLabel(task)} • {task.assigned_to_name ?? `Owner ${shortId(task.owner_id)}`}
                    </p>
                  </div>
                  {canWriteTasks ? (
                    <Button
                      disabled={completeTask.isPending && completeTask.variables === task.id}
                      onClick={() => completeTask.mutate(task.id)}
                      size="sm"
                      type="button"
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      Complete
                    </Button>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
