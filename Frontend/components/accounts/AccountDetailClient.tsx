"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Building2, Edit, Mail, Phone } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { AccountForm } from "@/components/accounts/AccountForm";
import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn, formatCurrency, formatDate } from "@/lib/utils";
import { usePermissions } from "@/lib/permissions";
import type { Account, AccountDeal, Activity as ActivityRecord, Contact } from "@/types/api";

type AccountTab = "contacts" | "deals" | "activity";

interface AccountDetailClientProps {
  accountId: string;
}

function formatTier(tier: string): string {
  return tier
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function TierPill({ tier }: { tier: string }) {
  const tone =
    tier === "enterprise"
      ? "bg-[#0F2444]/10 text-[#0F2444] ring-[#0F2444]/10"
      : tier === "startup"
        ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
        : "bg-blue-50 text-[#2563EB] ring-blue-100";

  return <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset", tone)}>{formatTier(tier)}</span>;
}

function addressLines(account: Account): string[] {
  return ["street", "city", "country"]
    .map((key) => account.address[key])
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0);
}

export function AccountDetailClient({ accountId }: AccountDetailClientProps) {
  const { canWriteAccounts } = usePermissions();
  const [tab, setTab] = useState<AccountTab>("contacts");
  const [editOpen, setEditOpen] = useState(false);

  const accountQuery = useQuery({
    queryFn: () => api.get<Account>(`/accounts/${accountId}`),
    queryKey: ["accounts", "detail", accountId],
  });
  const contactsQuery = useQuery({
    queryFn: () => api.get<Contact[]>(`/accounts/${accountId}/contacts`, { page_size: 20 }),
    queryKey: ["accounts", "contacts", accountId],
  });
  const dealsQuery = useQuery({
    queryFn: () => api.get<AccountDeal[]>(`/accounts/${accountId}/deals`, { page_size: 20 }),
    queryKey: ["accounts", "deals", accountId],
  });
  const activitiesQuery = useQuery({
    queryFn: () => api.get<ActivityRecord[]>("/activities/", { account_id: accountId, page_size: 20 }),
    queryKey: ["accounts", "activities", accountId],
  });

  const account = accountQuery.data;
  const contactColumns = useMemo<Array<DataTableColumn<Contact>>>(
    () => [
      {
        cell: (contact) => (
          <Link className="font-semibold text-[#0F2444] hover:text-[#2563EB]" href={`/contacts/${contact.id}`}>
            {contact.first_name} {contact.last_name}
          </Link>
        ),
        header: "Name",
        id: "name",
      },
      { accessor: "email", header: "Email", id: "email" },
      { accessor: "title", header: "Title", id: "title" },
      { cell: (contact) => contact.owner_name ?? contact.owner_id.slice(0, 8), header: "Owner", id: "owner" },
    ],
    [],
  );
  const dealColumns = useMemo<Array<DataTableColumn<AccountDeal>>>(
    () => [
      {
        cell: (deal) => (
          <Link className="font-semibold text-[#0F2444] hover:text-[#2563EB]" href={`/deals/${deal.id}`}>
            {deal.title}
          </Link>
        ),
        header: "Title",
        id: "title",
      },
      { cell: (deal) => deal.stage_name ?? "Unknown", header: "Stage", id: "stage" },
      { cell: (deal) => formatCurrency(Number(deal.value), deal.currency), header: "Value", id: "value" },
      { cell: (deal) => <StatusPill status={deal.status} type="deal" />, header: "Status", id: "status" },
    ],
    [],
  );

  if (accountQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <Skeleton className="h-32 rounded-xl" />
        <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </div>
    );
  }

  if (accountQuery.isError || !account) {
    return <div className="rounded-xl border border-red-100 bg-white p-5 text-sm text-red-700 shadow-sm">Could not load account.</div>;
  }

  const tabs: Array<{ label: string; value: AccountTab }> = [
    { label: "Contacts", value: "contacts" },
    { label: "Deals", value: "deals" },
    { label: "Activity", value: "activity" },
  ];

  return (
    <div className="grid gap-6">
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
                <Building2 className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-normal text-[#0F2444]">{account.name}</h1>
                <p className="mt-1 text-sm text-[#64748B]">{account.owner_name ?? account.owner_id.slice(0, 8)}</p>
              </div>
              <TierPill tier={account.tier} />
            </div>
            <a className="mt-4 inline-flex text-sm font-medium text-[#2563EB] hover:underline" href={account.website} rel="noreferrer" target="_blank">
              {account.website}
            </a>
          </div>
          {canWriteAccounts ? (
            <Button onClick={() => setEditOpen(true)} type="button" variant="outline">
              <Edit className="h-4 w-4" aria-hidden="true" />
              Edit
            </Button>
          ) : null}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <section className="rounded-xl bg-white p-5 shadow-sm">
          <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-4">
            {tabs.map((item) => (
              <button
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  tab === item.value ? "bg-[#2563EB] text-white" : "bg-slate-100 text-[#64748B] hover:bg-slate-200",
                )}
                key={item.value}
                onClick={() => setTab(item.value)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="mt-5">
            {tab === "contacts" ? (
              <DataTable
                columns={contactColumns}
                data={contactsQuery.data ?? []}
                emptyMessage="No linked contacts."
                getRowKey={(contact) => contact.id}
                isLoading={contactsQuery.isLoading}
              />
            ) : null}

            {tab === "deals" ? (
              <DataTable
                columns={dealColumns}
                data={dealsQuery.data ?? []}
                emptyMessage="No linked deals."
                getRowKey={(deal) => deal.id}
                isLoading={dealsQuery.isLoading}
              />
            ) : null}

            {tab === "activity" ? (
              <div className="space-y-3">
                {activitiesQuery.isLoading
                  ? [1, 2, 3].map((item) => <Skeleton className="h-20 rounded-lg" key={item} />)
                  : null}
                {!activitiesQuery.isLoading && (activitiesQuery.data ?? []).length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-[#64748B]">No account activity.</div>
                ) : null}
                {!activitiesQuery.isLoading
                  ? (activitiesQuery.data ?? []).map((activity) => (
                      <article className="flex gap-3 rounded-xl border border-slate-100 p-4" key={activity.id}>
                        <div className="grid h-10 w-10 place-items-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
                          {activity.type === "email" ? <Mail className="h-5 w-5" aria-hidden="true" /> : null}
                          {activity.type === "call" ? <Phone className="h-5 w-5" aria-hidden="true" /> : null}
                          {activity.type !== "email" && activity.type !== "call" ? <Activity className="h-5 w-5" aria-hidden="true" /> : null}
                        </div>
                        <div>
                          <h3 className="font-semibold text-[#0F2444]">{activity.subject}</h3>
                          <p className="mt-1 text-sm text-[#64748B]">{formatDate(activity.completed_at ?? activity.scheduled_at ?? activity.created_at)}</p>
                          {activity.outcome ? <p className="mt-2 text-sm text-slate-700">{activity.outcome}</p> : null}
                        </div>
                      </article>
                    ))
                  : null}
              </div>
            ) : null}
          </div>
        </section>

        <aside className="grid gap-4 content-start">
          <section className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-[#0F2444]">Account Info</h2>
            <dl className="mt-4 grid gap-3 text-sm">
              <div>
                <dt className="text-[#64748B]">Industry</dt>
                <dd className="mt-1 font-medium text-[#0F2444]">{account.industry}</dd>
              </div>
              <div>
                <dt className="text-[#64748B]">Size</dt>
                <dd className="mt-1 font-medium text-[#0F2444]">{account.size}</dd>
              </div>
              <div>
                <dt className="text-[#64748B]">Address</dt>
                <dd className="mt-1 font-medium text-[#0F2444]">{addressLines(account).join(", ") || "Not set"}</dd>
              </div>
              {Object.entries(account.custom_fields).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-[#64748B]">{key}</dt>
                  <dd className="mt-1 font-medium text-[#0F2444]">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-[#0F2444]">Totals</h2>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-[#EFF6FF] p-3">
                <p className="text-xs font-medium text-[#64748B]">Contacts</p>
                <p className="mt-1 text-2xl font-bold text-[#0F2444]">{account.linked_contact_count}</p>
              </div>
              <div className="rounded-lg bg-[#EFF6FF] p-3">
                <p className="text-xs font-medium text-[#64748B]">Deal Value</p>
                <p className="mt-1 text-2xl font-bold text-[#0F2444]">{formatCurrency(Number(account.total_deal_value ?? 0))}</p>
              </div>
            </div>
          </section>
        </aside>
      </div>

      {canWriteAccounts ? <AccountForm account={account} onOpenChange={setEditOpen} onSaved={() => void accountQuery.refetch()} open={editOpen} /> : null}
    </div>
  );
}
