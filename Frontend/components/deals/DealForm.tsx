"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetBody, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { api } from "@/lib/api";
import type { Account, Contact, Deal, DealCreate, DealUpdate, Pipeline, User } from "@/types/api";

const dealTypes = ["new_business", "renewal", "upsell"] as const;

const dealFormSchema = z.object({
  account_id: z.string().min(1, "Account is required."),
  contact_id: z.string().min(1, "Contact is required."),
  currency: z.string().min(3).max(3),
  expected_close: z.string().min(1, "Expected close is required."),
  owner_id: z.string().optional(),
  pipeline_id: z.string().min(1, "Pipeline is required."),
  stage_id: z.string().min(1, "Stage is required."),
  title: z.string().min(1, "Title is required."),
  type: z.enum(dealTypes),
  value: z.string().min(1, "Value is required."),
});

type DealFormValues = z.infer<typeof dealFormSchema>;

interface DealFormProps {
  deal?: Deal | null;
  onOpenChange: (open: boolean) => void;
  onSaved?: (deal: Deal) => void;
  open: boolean;
  selectedPipelineId?: string;
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timeoutId);
  }, [delayMs, value]);

  return debounced;
}

function addDaysDate(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function emptyValues(selectedPipelineId?: string): DealFormValues {
  return {
    account_id: "",
    contact_id: "",
    currency: "USD",
    expected_close: addDaysDate(30),
    owner_id: "",
    pipeline_id: selectedPipelineId ?? "",
    stage_id: "",
    title: "",
    type: "new_business",
    value: "",
  };
}

function valuesFromDeal(deal?: Deal | null, selectedPipelineId?: string): DealFormValues {
  if (!deal) {
    return emptyValues(selectedPipelineId);
  }

  return {
    account_id: deal.account_id,
    contact_id: deal.contact_id,
    currency: deal.currency,
    expected_close: deal.expected_close.slice(0, 10),
    owner_id: deal.owner_id,
    pipeline_id: deal.pipeline_id,
    stage_id: deal.stage_id,
    title: deal.title,
    type: dealTypes.includes(deal.type as (typeof dealTypes)[number]) ? (deal.type as (typeof dealTypes)[number]) : "new_business",
    value: String(deal.value),
  };
}

function fieldError(message?: string) {
  return message ? <p className="mt-1 text-xs text-red-600">{message}</p> : null;
}

function optionLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function buildPayload(values: DealFormValues): DealCreate | DealUpdate {
  return {
    account_id: values.account_id,
    contact_id: values.contact_id,
    currency: values.currency.toUpperCase(),
    expected_close: values.expected_close,
    owner_id: values.owner_id || null,
    pipeline_id: values.pipeline_id,
    stage_id: values.stage_id,
    title: values.title,
    type: values.type,
    value: Number(values.value),
  };
}

export function DealForm({ deal, onOpenChange, onSaved, open, selectedPipelineId }: DealFormProps) {
  const queryClient = useQueryClient();
  const [contactSearch, setContactSearch] = useState(deal?.contact_name ?? "");
  const [accountSearch, setAccountSearch] = useState(deal?.account_name ?? "");
  const debouncedContactSearch = useDebouncedValue(contactSearch, 300);
  const debouncedAccountSearch = useDebouncedValue(accountSearch, 300);
  const form = useForm<DealFormValues>({
    defaultValues: valuesFromDeal(deal, selectedPipelineId),
    resolver: zodResolver(dealFormSchema),
  });
  const selectedPipeline = form.watch("pipeline_id");

  const pipelinesQuery = useQuery({
    queryFn: () => api.get<Pipeline[]>("/pipelines/"),
    queryKey: ["pipelines", "deal-form"],
  });
  const contactsQuery = useQuery({
    queryFn: () => api.get<Contact[]>("/contacts/", { page_size: 50, search: debouncedContactSearch || undefined }),
    queryKey: ["contacts", "deal-form", debouncedContactSearch],
  });
  const accountsQuery = useQuery({
    queryFn: () => api.get<Account[]>("/accounts/", { page_size: 100, search: debouncedAccountSearch || undefined }),
    queryKey: ["accounts", "deal-form", debouncedAccountSearch],
  });
  const usersQuery = useQuery({
    queryFn: () => api.get<User[]>("/users/"),
    queryKey: ["users", "deal-form"],
    retry: false,
  });

  const pipelines = pipelinesQuery.data ?? [];
  const activePipeline = pipelines.find((pipeline) => pipeline.id === selectedPipeline) ?? pipelines.find((pipeline) => pipeline.is_default) ?? pipelines[0];
  const stages = activePipeline?.stages ?? [];

  useEffect(() => {
    if (open) {
      form.reset(valuesFromDeal(deal, selectedPipelineId));
      setContactSearch(deal?.contact_name ?? "");
      setAccountSearch(deal?.account_name ?? "");
    }
  }, [deal, form, open, selectedPipelineId]);

  useEffect(() => {
    if (!form.getValues("pipeline_id") && activePipeline?.id) {
      form.setValue("pipeline_id", activePipeline.id, { shouldDirty: true });
    }
  }, [activePipeline?.id, form]);

  useEffect(() => {
    const currentStage = form.getValues("stage_id");
    if (stages.length > 0 && (!currentStage || !stages.some((stage) => stage.id === currentStage))) {
      form.setValue("stage_id", stages[0].id, { shouldDirty: true });
    }
  }, [form, stages]);

  const contactOptions = useMemo(() => {
    const options = contactsQuery.data ?? [];
    const normalizedSearch = debouncedContactSearch.trim().toLowerCase();
    if (!normalizedSearch) {
      return options;
    }

    return options.filter((contact) =>
      `${contact.first_name} ${contact.last_name} ${contact.email}`.toLowerCase().includes(normalizedSearch),
    );
  }, [contactsQuery.data, debouncedContactSearch]);
  const accountOptions = useMemo(() => {
    const options = accountsQuery.data ?? [];
    const normalizedSearch = debouncedAccountSearch.trim().toLowerCase();
    if (!normalizedSearch) {
      return options;
    }

    return options.filter((account) => account.name.toLowerCase().includes(normalizedSearch));
  }, [accountsQuery.data, debouncedAccountSearch]);

  const saveDeal = useMutation({
    mutationFn: (values: DealFormValues) => {
      const payload = buildPayload(values);
      if (deal) {
        return api.patch<Deal, DealUpdate>(`/deals/${deal.id}`, payload as DealUpdate);
      }

      return api.post<Deal, DealCreate>("/deals/", payload as DealCreate);
    },
    onSuccess: (savedDeal) => {
      void queryClient.invalidateQueries({ queryKey: ["deals"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onSaved?.(savedDeal);
      onOpenChange(false);
    },
  });

  const submitting = saveDeal.isPending;

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{deal ? "Edit Deal" : "New Deal"}</SheetTitle>
          <SheetDescription>{deal ? "Update deal details and stage." : "Create a pipeline opportunity."}</SheetDescription>
        </SheetHeader>
        <form className="flex min-h-0 flex-1 flex-col" onSubmit={form.handleSubmit((values) => saveDeal.mutate(values))}>
          <SheetBody className="space-y-5">
            <div>
              <Label htmlFor="deal_title">Title</Label>
              <Input id="deal_title" disabled={submitting} {...form.register("title")} />
              {fieldError(form.formState.errors.title?.message)}
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <Label htmlFor="deal_type">Type</Label>
                <select
                  className="h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                  disabled={submitting}
                  id="deal_type"
                  {...form.register("type")}
                >
                  {dealTypes.map((type) => (
                    <option key={type} value={type}>
                      {optionLabel(type)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="deal_value">Value</Label>
                <Input id="deal_value" disabled={submitting} min="0" step="100" type="number" {...form.register("value")} />
                {fieldError(form.formState.errors.value?.message)}
              </div>
              <div>
                <Label htmlFor="deal_currency">Currency</Label>
                <Input id="deal_currency" disabled={submitting} maxLength={3} {...form.register("currency")} />
                {fieldError(form.formState.errors.currency?.message)}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="deal_pipeline">Pipeline</Label>
                <select
                  className="h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                  disabled={submitting}
                  id="deal_pipeline"
                  {...form.register("pipeline_id")}
                >
                  {pipelines.map((pipeline) => (
                    <option key={pipeline.id} value={pipeline.id}>
                      {pipeline.name}
                    </option>
                  ))}
                </select>
                {fieldError(form.formState.errors.pipeline_id?.message)}
              </div>
              <div>
                <Label htmlFor="deal_stage">Stage</Label>
                <select
                  className="h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                  disabled={submitting}
                  id="deal_stage"
                  {...form.register("stage_id")}
                >
                  {stages.map((stage) => (
                    <option key={stage.id} value={stage.id}>
                      {stage.name}
                    </option>
                  ))}
                </select>
                {fieldError(form.formState.errors.stage_id?.message)}
              </div>
            </div>

            <div>
              <Label htmlFor="expected_close">Expected Close</Label>
              <Input id="expected_close" disabled={submitting} type="date" {...form.register("expected_close")} />
              {fieldError(form.formState.errors.expected_close?.message)}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="contact_search">Contact</Label>
                <Input
                  id="contact_search"
                  disabled={submitting}
                  onChange={(event) => setContactSearch(event.target.value)}
                  placeholder="Search contacts"
                  value={contactSearch}
                />
                <select
                  className="mt-2 h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                  disabled={submitting}
                  {...form.register("contact_id")}
                >
                  <option value="">Choose contact</option>
                  {contactOptions.map((contact) => (
                    <option key={contact.id} value={contact.id}>
                      {contact.first_name} {contact.last_name}
                    </option>
                  ))}
                </select>
                {fieldError(form.formState.errors.contact_id?.message)}
              </div>
              <div>
                <Label htmlFor="account_search">Account</Label>
                <Input
                  id="account_search"
                  disabled={submitting}
                  onChange={(event) => setAccountSearch(event.target.value)}
                  placeholder="Search accounts"
                  value={accountSearch}
                />
                <select
                  className="mt-2 h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                  disabled={submitting}
                  {...form.register("account_id")}
                >
                  <option value="">Choose account</option>
                  {accountOptions.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
                {fieldError(form.formState.errors.account_id?.message)}
              </div>
            </div>

            <div>
              <Label htmlFor="deal_owner">Owner</Label>
              <select
                className="h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                disabled={submitting}
                id="deal_owner"
                {...form.register("owner_id")}
              >
                <option value="">Current user</option>
                {(usersQuery.data ?? [])
                  .filter((user) => user.is_active)
                  .map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name}
                    </option>
                  ))}
              </select>
            </div>

            {saveDeal.isError ? <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Could not save deal.</div> : null}
          </SheetBody>
          <SheetFooter>
            <Button disabled={submitting} onClick={() => onOpenChange(false)} type="button" variant="outline">
              Cancel
            </Button>
            <Button className="bg-[#2563EB] hover:bg-blue-700" disabled={submitting} type="submit">
              <Save className="h-4 w-4" aria-hidden="true" />
              Save Deal
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}
