"use client";

import { useQuery } from "@tanstack/react-query";
import { Filter } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { User } from "@/types/api";

export interface DateRangeFilterValue {
  date_from: string;
  date_to: string;
  owner_id: string;
}

interface DateRangeFilterProps {
  ownerLabel?: string;
  showOwner?: boolean;
  value: DateRangeFilterValue;
  onApply: (value: DateRangeFilterValue) => void;
}

export function defaultDateRange(): DateRangeFilterValue {
  const dateTo = new Date();
  const dateFrom = new Date();
  dateFrom.setDate(dateFrom.getDate() - 30);

  return {
    date_from: dateFrom.toISOString().slice(0, 10),
    date_to: dateTo.toISOString().slice(0, 10),
    owner_id: "",
  };
}

export function DateRangeFilter({ onApply, ownerLabel = "Owner", showOwner = true, value }: DateRangeFilterProps) {
  const [draft, setDraft] = useState<DateRangeFilterValue>(value);
  const usersQuery = useQuery({
    enabled: showOwner,
    queryFn: () => api.get<User[]>("/users/"),
    queryKey: ["users", "report-filter"],
    retry: false,
  });

  useEffect(() => {
    setDraft(value);
  }, [value]);

  return (
    <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto]">
      <Input
        aria-label="Date from"
        onChange={(event) => setDraft((current) => ({ ...current, date_from: event.target.value }))}
        type="date"
        value={draft.date_from}
      />
      <Input
        aria-label="Date to"
        onChange={(event) => setDraft((current) => ({ ...current, date_to: event.target.value }))}
        type="date"
        value={draft.date_to}
      />
      {showOwner ? (
        <select
          aria-label={ownerLabel}
          className="h-10 rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
          onChange={(event) => setDraft((current) => ({ ...current, owner_id: event.target.value }))}
          value={draft.owner_id}
        >
          <option value="">All {ownerLabel.toLowerCase()}s</option>
          {(usersQuery.data ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </select>
      ) : (
        <span className="hidden md:block" />
      )}
      <Button onClick={() => onApply(draft)} type="button" variant="outline">
        <Filter className="h-4 w-4" aria-hidden="true" />
        Apply
      </Button>
    </div>
  );
}
