"use client";

import { isBefore, startOfToday } from "date-fns";
import { AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

import { cn, formatCurrency, formatDate, getInitials } from "@/lib/utils";
import type { Deal, DealSummary } from "@/types/api";

interface DealCardProps {
  deal: DealSummary;
  detail?: Deal;
  isDragging?: boolean;
}

function toNumber(value: number | string): number {
  return typeof value === "number" ? value : Number(value);
}

export function DealCard({ deal, detail, isDragging = false }: DealCardProps) {
  const router = useRouter();
  const isOverdue = deal.status === "open" && isBefore(new Date(deal.expected_close), startOfToday());
  const ownerName = detail?.owner_name ?? "Owner";
  const accountName = detail?.account_name ?? `Account ${deal.account_id.slice(0, 8)}`;
  const contactName = detail?.contact_name ?? `Contact ${deal.contact_id.slice(0, 8)}`;

  return (
    <button
      className={cn(
        "w-full rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-200 hover:shadow-md",
        isDragging && "rotate-1 border-blue-300 shadow-lg",
      )}
      onClick={() => router.push(`/deals/${deal.id}`)}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="line-clamp-2 text-sm font-bold text-[#0F2444]">{deal.title}</h3>
        {isOverdue ? <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" aria-label="Expected close is overdue" /> : null}
      </div>
      <p className="mt-2 truncate text-xs text-[#64748B]">
        {accountName} • {contactName}
      </p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-[#0F2444]">{formatCurrency(toNumber(deal.value), deal.currency)}</p>
        <span className="rounded-full bg-[#EFF6FF] px-2 py-1 text-xs font-semibold text-[#2563EB]">{Math.round(deal.probability)}%</span>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <p className={cn("text-xs font-medium", isOverdue ? "text-red-600" : "text-[#64748B]")}>{formatDate(deal.expected_close)}</p>
        <div className="grid h-7 w-7 place-items-center rounded-full bg-[#0F2444] text-xs font-semibold text-white" title={ownerName}>
          {getInitials(ownerName)}
        </div>
      </div>
    </button>
  );
}
