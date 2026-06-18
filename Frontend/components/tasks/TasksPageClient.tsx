"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isBefore } from "date-fns";
import { AlertTriangle, Check, Clock, Edit, Plus } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { ActivityTypeIcon } from "@/components/activities/ActivityTypeIcon";
import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { StatusPill } from "@/components/shared/StatusPill";
import { SnoozeModal } from "@/components/tasks/SnoozeModal";
import { TaskForm } from "@/components/tasks/TaskForm";
import { Button } from "@/components/ui/button";
import { authClient } from "@/lib/auth-client";
import { normalizeRole } from "@/lib/auth-types";
import { api } from "@/lib/api";
import { usePermissions } from "@/lib/permissions";
import { cn, formatDate } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import type { Account, Contact, Deal, Lead, Task, TaskPriority, User } from "@/types/api";

type TaskTab = "mine" | "all";

const PAGE_SIZE = 20;

function stringOrUndefined(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function isUuid(value: string | undefined): value is string {
  return Boolean(value && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value));
}

function contactName(contact: Contact): string {
  return `${contact.first_name} ${contact.last_name}`;
}

function priorityPill(priority: TaskPriority) {
  const tone: Record<TaskPriority, string> = {
    high: "bg-red-50 text-red-700 ring-red-100",
    low: "bg-slate-100 text-[#64748B] ring-slate-200",
    medium: "bg-blue-50 text-[#2563EB] ring-blue-100",
    urgent: "bg-red-100 text-red-800 ring-red-200",
  };

  return (
    <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-medium ring-1 ring-inset", tone[priority])}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
}

function isOverdue(task: Task): boolean {
  return Boolean(task.due_at && task.status !== "completed" && isBefore(new Date(task.due_at), new Date()));
}

export function TasksPageClient() {
  const queryClient = useQueryClient();
  const { canWriteTasks } = usePermissions();
  const session = authClient.useSession();
  const storedUser = useAuthStore((state) => state.user);
  const sessionUser = session.data?.user;
  const role = normalizeRole(sessionUser?.role ?? storedUser?.role);
  const canSeeAll = role === "super_admin" || role === "sales_manager";
  const fallbackSessionId = stringOrUndefined(sessionUser?.id) ?? storedUser?.id;
  const meQuery = useQuery({
    queryFn: () => api.get<User>("/users/me"),
    queryKey: ["users", "me"],
    retry: false,
  });
  const currentUserId = meQuery.data?.id ?? (isUuid(fallbackSessionId) ? fallbackSessionId : undefined);
  const [tab, setTab] = useState<TaskTab>("mine");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [snoozingTask, setSnoozingTask] = useState<Task | null>(null);
  const [completedTaskId, setCompletedTaskId] = useState<string | null>(null);

  const tasksQuery = useQuery({
    enabled: tab === "all" || Boolean(currentUserId),
    queryFn: () =>
      api.get<Task[]>("/tasks/", {
        owner_id: tab === "mine" ? currentUserId : undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    queryKey: ["tasks", "list", tab, currentUserId, page],
  });
  const overdueQuery = useQuery({
    queryFn: () => api.get<Task[]>("/tasks/overdue", { owner_id: tab === "mine" ? currentUserId : undefined, page_size: 100 }),
    queryKey: ["tasks", "overdue", tab, currentUserId],
  });
  const usersQuery = useQuery({ queryFn: () => api.get<User[]>("/users/"), queryKey: ["users", "task-page"], retry: false });
  const leadsQuery = useQuery({ queryFn: () => api.get<Lead[]>("/leads/", { page_size: 100 }), queryKey: ["leads", "task-page"] });
  const contactsQuery = useQuery({ queryFn: () => api.get<Contact[]>("/contacts/", { page_size: 100 }), queryKey: ["contacts", "task-page"] });
  const dealsQuery = useQuery({ queryFn: () => api.get<Deal[]>("/deals/", { page_size: 100 }), queryKey: ["deals", "task-page"] });
  const accountsQuery = useQuery({ queryFn: () => api.get<Account[]>("/accounts/", { page_size: 100 }), queryKey: ["accounts", "task-page"] });

  const completeTask = useMutation({
    mutationFn: (id: string) => api.post<Task>(`/tasks/${id}/complete`),
    onMutate: async (id) => {
      const listKey = ["tasks", "list", tab, currentUserId, page] as const;
      const overdueKey = ["tasks", "overdue", tab, currentUserId] as const;
      await Promise.all([
        queryClient.cancelQueries({ queryKey: listKey }),
        queryClient.cancelQueries({ queryKey: overdueKey }),
      ]);
      const previousTasks = queryClient.getQueryData<Task[]>(listKey);
      const previousOverdue = queryClient.getQueryData<Task[]>(overdueKey);
      const completedAt = new Date().toISOString();

      queryClient.setQueryData<Task[]>(listKey, (current) =>
        (current ?? []).map((task) => (task.id === id ? { ...task, completed_at: completedAt, status: "completed" } : task)),
      );
      queryClient.setQueryData<Task[]>(overdueKey, (current) => (current ?? []).filter((task) => task.id !== id));

      return { listKey, overdueKey, previousOverdue, previousTasks };
    },
    onError: (_error, _id, context) => {
      if (context?.previousTasks) {
        queryClient.setQueryData(context.listKey, context.previousTasks);
      }
      if (context?.previousOverdue) {
        queryClient.setQueryData(context.overdueKey, context.previousOverdue);
      }
    },
    onSuccess: (_task, id) => {
      setCompletedTaskId(id);
      window.setTimeout(() => setCompletedTaskId(null), 800);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const userMap = useMemo(() => new Map((usersQuery.data ?? []).map((user) => [user.id, user.full_name])), [usersQuery.data]);
  const leadMap = useMemo(() => new Map((leadsQuery.data ?? []).map((lead) => [lead.id, lead.full_name])), [leadsQuery.data]);
  const contactMap = useMemo(() => new Map((contactsQuery.data ?? []).map((contact) => [contact.id, contactName(contact)])), [contactsQuery.data]);
  const dealMap = useMemo(() => new Map((dealsQuery.data ?? []).map((deal) => [deal.id, deal.title])), [dealsQuery.data]);
  const accountMap = useMemo(() => new Map((accountsQuery.data ?? []).map((account) => [account.id, account.name])), [accountsQuery.data]);

  const tasks = tasksQuery.data ?? [];
  const overdueCount = overdueQuery.data?.length ?? 0;
  const columns = useMemo<Array<DataTableColumn<Task>>>(
    () => [
      { cell: (task) => priorityPill(task.priority), header: "Priority", id: "priority" },
      { accessor: "title", header: "Title", id: "title" },
      { cell: (task) => <ActivityTypeIcon className="h-5 w-5 text-[#2563EB]" type={task.type ?? "task"} />, header: "Type", id: "type" },
      {
        cell: (task) => {
          if (task.contact_id) return <Link className="text-[#2563EB] hover:underline" href={`/contacts/${task.contact_id}`}>{contactMap.get(task.contact_id) ?? "Contact"}</Link>;
          if (task.deal_id) return <Link className="text-[#2563EB] hover:underline" href={`/deals/${task.deal_id}`}>{dealMap.get(task.deal_id) ?? "Deal"}</Link>;
          if (task.lead_id) return <Link className="text-[#2563EB] hover:underline" href={`/leads/${task.lead_id}`}>{leadMap.get(task.lead_id) ?? "Lead"}</Link>;
          if (task.account_id) return <Link className="text-[#2563EB] hover:underline" href={`/accounts/${task.account_id}`}>{accountMap.get(task.account_id) ?? "Account"}</Link>;
          return <span className="text-[#64748B]">No link</span>;
        },
        header: "Linked To",
        id: "linked",
      },
      { cell: (task) => userMap.get(task.owner_id) ?? task.owner_id.slice(0, 8), header: "Assigned To", id: "assigned" },
      {
        cell: (task) => {
          const overdue = isOverdue(task);
          return (
            <span className={cn("inline-flex items-center gap-1 font-medium", overdue ? "text-red-600" : "text-[#64748B]")}>
              {overdue ? <AlertTriangle className="h-4 w-4" aria-hidden="true" /> : null}
              {task.due_at ? formatDate(task.due_at) : "No due date"}
            </span>
          );
        },
        header: "Due Date",
        id: "due",
      },
      { cell: (task) => <StatusPill status={isOverdue(task) ? "overdue" : task.status} type="task" />, header: "Status", id: "status" },
      {
        cell: (task) => canWriteTasks ? (
          <div className="relative flex items-center gap-1">
            {completedTaskId === task.id ? <span className="task-complete-pop pointer-events-none absolute -left-1 text-emerald-600">✓</span> : null}
            <Button disabled={task.status === "completed" || completeTask.isPending} onClick={() => completeTask.mutate(task.id)} size="icon" type="button" variant="ghost">
              <Check className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Complete</span>
            </Button>
            <Button onClick={() => setSnoozingTask(task)} size="icon" type="button" variant="ghost">
              <Clock className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Snooze</span>
            </Button>
            <Button onClick={() => setEditingTask(task)} size="icon" type="button" variant="ghost">
              <Edit className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Edit</span>
            </Button>
          </div>
        ) : null,
        header: "Actions",
        id: "actions",
      },
    ],
    [accountMap, canWriteTasks, completeTask, completedTaskId, contactMap, dealMap, leadMap, userMap],
  );

  function changeTab(nextTab: TaskTab) {
    setTab(nextTab);
    setPage(1);
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        primaryAction={canWriteTasks ? { icon: Plus, label: "New Task", onClick: () => setFormOpen(true) } : undefined}
        subtitle="Track follow-ups, overdue work, and task assignments."
        title="Tasks"
      />

      {overdueCount > 0 ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700 shadow-sm">
          {overdueCount} overdue task{overdueCount === 1 ? "" : "s"} need attention.
        </div>
      ) : null}

      <section className="rounded-xl bg-white p-2 shadow-sm">
        <div className="flex gap-2">
          <button className={cn("rounded-md px-4 py-2 text-sm font-semibold", tab === "mine" ? "bg-[#2563EB] text-white" : "text-[#64748B] hover:bg-slate-100")} onClick={() => changeTab("mine")} type="button">
            My Tasks
          </button>
          {canSeeAll ? (
            <button className={cn("rounded-md px-4 py-2 text-sm font-semibold", tab === "all" ? "bg-[#2563EB] text-white" : "text-[#64748B] hover:bg-slate-100")} onClick={() => changeTab("all")} type="button">
              All Tasks
            </button>
          ) : null}
        </div>
      </section>

      {!currentUserId && tab === "mine" && !meQuery.isLoading ? (
        <div className="rounded-xl border border-amber-100 bg-white p-4 text-sm text-amber-800 shadow-sm">Could not identify the backend user session yet.</div>
      ) : null}

      <DataTable
        columns={columns}
        data={tasks}
        emptyMessage="No tasks found."
        getRowKey={(task) => task.id}
        isLoading={tasksQuery.isLoading}
        pagination={{ hasNextPage: tasks.length === PAGE_SIZE, page, pageSize: PAGE_SIZE, onPageChange: setPage }}
      />

      {tasksQuery.isError ? <div className="rounded-xl border border-red-100 bg-white p-4 text-sm text-red-700 shadow-sm">Could not load tasks.</div> : null}

      {canWriteTasks ? (
        <>
          <TaskForm onOpenChange={setFormOpen} open={formOpen} />
          <TaskForm onOpenChange={(open) => (!open ? setEditingTask(null) : undefined)} open={Boolean(editingTask)} task={editingTask} />
          <SnoozeModal onOpenChange={(open) => (!open ? setSnoozingTask(null) : undefined)} open={Boolean(snoozingTask)} task={snoozingTask} />
        </>
      ) : null}
    </div>
  );
}
