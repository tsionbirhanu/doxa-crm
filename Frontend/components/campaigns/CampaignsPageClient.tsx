"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CampaignForm } from "@/components/campaigns/CampaignForm";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { usePermissions } from "@/lib/permissions";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Campaign, CampaignStatus, CampaignType } from "@/types/api";

const campaignTypes: CampaignType[] = ["email", "event", "social", "cold_call"];
const campaignStatuses: CampaignStatus[] = ["draft", "active", "paused", "completed"];

function optionLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function typePill(type: CampaignType) {
  return <span className="rounded-full bg-[#EFF6FF] px-2.5 py-1 text-xs font-medium text-[#2563EB]">{optionLabel(type)}</span>;
}

export function CampaignsPageClient() {
  const { canWriteCampaigns } = usePermissions();
  const [formOpen, setFormOpen] = useState(false);
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const campaignsQuery = useQuery({
    queryFn: () =>
      api.get<Campaign[]>("/campaigns/", {
        page_size: 100,
        status: status || undefined,
        type: type || undefined,
      }),
    queryKey: ["campaigns", "list", status, type],
  });
  const campaigns = campaignsQuery.data ?? [];

  return (
    <div className="grid gap-6">
      <PageHeader
        primaryAction={canWriteCampaigns ? { icon: Plus, label: "New Campaign", onClick: () => setFormOpen(true) } : undefined}
        subtitle="Build email sequences, enroll contacts, and track performance."
        title="Campaigns"
      />

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-2">
          <select className="h-10 rounded-md border border-[var(--input)] bg-white px-3 text-sm" onChange={(event) => setStatus(event.target.value)} value={status}>
            <option value="">All statuses</option>
            {campaignStatuses.map((item) => (
              <option key={item} value={item}>
                {optionLabel(item)}
              </option>
            ))}
          </select>
          <select className="h-10 rounded-md border border-[var(--input)] bg-white px-3 text-sm" onChange={(event) => setType(event.target.value)} value={type}>
            <option value="">All types</option>
            {campaignTypes.map((item) => (
              <option key={item} value={item}>
                {optionLabel(item)}
              </option>
            ))}
          </select>
        </div>
      </section>

      {campaignsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((item) => (
            <Skeleton className="h-64 rounded-xl" key={item} />
          ))}
        </div>
      ) : null}

      {!campaignsQuery.isLoading && campaigns.length === 0 ? (
        <div className="rounded-xl bg-white p-8 text-center text-sm text-[#64748B] shadow-sm">No campaigns found.</div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {campaigns.map((campaign) => (
          <Link className="rounded-xl bg-white p-5 shadow-sm transition hover:shadow-md" href={`/campaigns/${campaign.id}`} key={campaign.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="truncate text-lg font-semibold text-[#0F2444]">{campaign.name}</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {typePill(campaign.type)}
                  <StatusPill status={campaign.status} type="campaign" />
                </div>
              </div>
              <div className="grid h-10 w-10 place-items-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
                <CalendarDays className="h-5 w-5" aria-hidden="true" />
              </div>
            </div>

            <div className="mt-5 grid grid-cols-3 gap-3">
              <div>
                <p className="text-xs text-[#64748B]">Sent</p>
                <p className="text-xl font-bold text-[#0F2444]">{campaign.metrics.sent}</p>
              </div>
              <div>
                <p className="text-xs text-[#64748B]">Opened</p>
                <p className="text-xl font-bold text-[#0F2444]">{campaign.metrics.opened}</p>
              </div>
              <div>
                <p className="text-xs text-[#64748B]">Clicked</p>
                <p className="text-xl font-bold text-[#0F2444]">{campaign.metrics.clicked}</p>
              </div>
            </div>

            <div className="mt-5 grid gap-2 text-sm text-[#64748B]">
              <p>{campaign.enrollment_count} enrolled contacts</p>
              <p>
                {formatDate(campaign.start_date)} - {formatDate(campaign.end_date)}
              </p>
              <p>{formatCurrency(Number(campaign.budget ?? 0))} budget</p>
            </div>
          </Link>
        ))}
      </div>

      {campaignsQuery.isError ? <div className="rounded-xl border border-red-100 bg-white p-4 text-sm text-red-700 shadow-sm">Could not load campaigns.</div> : null}
      {canWriteCampaigns ? <CampaignForm onOpenChange={setFormOpen} open={formOpen} /> : null}
    </div>
  );
}
