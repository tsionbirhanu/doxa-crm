"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit, Plus, ShieldCheck, ToggleLeft, ToggleRight } from "lucide-react";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { StatusPill } from "@/components/shared/StatusPill";
import { UserForm } from "@/components/settings/UserForm";
import { Button } from "@/components/ui/button";
import { authClient } from "@/lib/auth-client";
import { formatDate } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import type { User, UserUpdate } from "@/types/api";

function statusBadge(active: boolean) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${active ? "bg-emerald-50 text-emerald-700 ring-emerald-100" : "bg-slate-100 text-[#64748B] ring-slate-200"}`}>
      {active ? "Active" : "Inactive"}
    </span>
  );
}

export function UsersSettingsClient() {
  const queryClient = useQueryClient();
  const session = authClient.useSession();
  const storedUser = useAuthStore((state) => state.user);
  const currentUserId = String(session.data?.user?.id ?? storedUser?.id ?? "");
  const [formOpen, setFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [userToToggle, setUserToToggle] = useState<User | null>(null);

  const usersQuery = useQuery({
    queryFn: () => api.get<User[]>("/users/"),
    queryKey: ["users", "settings"],
  });

  const toggleUser = useMutation({
    mutationFn: (user: User) =>
      api.patch<User, UserUpdate>(`/users/${user.id}`, {
        is_active: !user.is_active,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  function openCreateForm() {
    setEditingUser(null);
    setFormOpen(true);
  }

  function openEditForm(user: User) {
    setEditingUser(user);
    setFormOpen(true);
  }

  const columns = useMemo<Array<DataTableColumn<User>>>(
    () => [
      {
        cell: (user) => (
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[#0F2444]">{user.full_name}</span>
            {user.id === currentUserId ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-[#EFF6FF] px-2 py-0.5 text-[11px] font-semibold text-[#2563EB]">
                <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                You
              </span>
            ) : null}
          </div>
        ),
        header: "Name",
        id: "name",
      },
      { accessor: "email", header: "Email", id: "email" },
      { cell: (user) => <StatusPill status={user.role} type="role" />, header: "Role", id: "role" },
      { cell: (user) => statusBadge(user.is_active), header: "Status", id: "status" },
      { cell: (user) => formatDate(user.created_at), header: "Created", id: "created" },
      {
        cell: (user) => {
          const isCurrentUser = user.id === currentUserId;
          return (
            <div className="flex items-center gap-2">
              <Button onClick={() => openEditForm(user)} size="sm" type="button" variant="outline">
                <Edit className="h-4 w-4" aria-hidden="true" />
                Edit
              </Button>
              <Button
                disabled={isCurrentUser || toggleUser.isPending}
                onClick={() => setUserToToggle(user)}
                size="sm"
                title={isCurrentUser ? "You cannot deactivate yourself." : undefined}
                type="button"
                variant="outline"
              >
                {user.is_active ? <ToggleRight className="h-4 w-4 text-emerald-600" aria-hidden="true" /> : <ToggleLeft className="h-4 w-4" aria-hidden="true" />}
                {user.is_active ? "Deactivate" : "Activate"}
              </Button>
            </div>
          );
        },
        header: "Actions",
        id: "actions",
      },
    ],
    [currentUserId, toggleUser],
  );

  return (
    <div className="grid gap-6">
      <PageHeader
        primaryAction={{ icon: Plus, label: "Invite User", onClick: openCreateForm }}
        subtitle="Manage CRM users, roles, and access status."
        title="User Management"
      />

      <DataTable
        columns={columns}
        data={usersQuery.data ?? []}
        emptyMessage="No users found."
        getRowClassName={(user) => (user.id === currentUserId ? "bg-[#EFF6FF]/60" : undefined)}
        getRowKey={(user) => user.id}
        isLoading={usersQuery.isLoading}
      />

      {usersQuery.isError ? <div className="rounded-xl border border-red-100 bg-white p-4 text-sm text-red-700 shadow-sm">Could not load users.</div> : null}

      <UserForm onOpenChange={setFormOpen} open={formOpen} user={editingUser} />
      <ConfirmDialog
        isPending={toggleUser.isPending}
        onConfirm={() => {
          if (userToToggle) {
            toggleUser.mutate(userToToggle, {
              onSuccess: () => setUserToToggle(null),
            });
          }
        }}
        onOpenChange={(open) => {
          if (!open) {
            setUserToToggle(null);
          }
        }}
        open={Boolean(userToToggle)}
        title={userToToggle?.is_active ? "Deactivate user" : "Activate user"}
      />
    </div>
  );
}
