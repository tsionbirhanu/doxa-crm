"use client";

import { DragDropContext, Draggable, Droppable, type DropResult } from "@hello-pangea/dnd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GripVertical, Pause, Play, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import type { CSSProperties } from "react";
import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CampaignForm } from "@/components/campaigns/CampaignForm";
import { ContactSelectModal } from "@/components/campaigns/ContactSelectModal";
import { SequenceStepForm } from "@/components/campaigns/SequenceStepForm";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn, formatCurrency, formatDate } from "@/lib/utils";
import type {
  Campaign,
  CampaignEnrollment,
  CampaignMetrics,
  CampaignSequenceStep,
  CampaignStepsReorderRequest,
} from "@/types/api";

type CampaignTab = "overview" | "sequence" | "enrollments" | "metrics";

interface CampaignDetailClientProps {
  campaignId: string;
}

function optionLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function rate(numerator: number, denominator: number): number {
  return denominator > 0 ? Math.round((numerator / denominator) * 1000) / 10 : 0;
}

function preview(body?: string | null): string {
  if (!body) {
    return "No body yet.";
  }

  return body.length > 140 ? `${body.slice(0, 140)}...` : body;
}

function metricChartData(metrics?: CampaignMetrics) {
  const current = metrics ?? { clicked: 0, converted: 0, opened: 0, replied: 0, sent: 0 };
  return [
    { clicked: 0, label: "Start", opened: 0, sent: 0 },
    { clicked: current.clicked, label: "Current", opened: current.opened, sent: current.sent },
  ];
}

function variantRows(steps: CampaignSequenceStep[]) {
  const variants = new Map<string, { count: number; subjects: string[] }>();
  steps.forEach((step) => {
    if (!step.variant) {
      return;
    }
    const row = variants.get(step.variant) ?? { count: 0, subjects: [] };
    row.count += 1;
    row.subjects.push(step.subject);
    variants.set(step.variant, row);
  });
  return Array.from(variants.entries()).map(([variant, data]) => ({ variant, ...data }));
}

export function CampaignDetailClient({ campaignId }: CampaignDetailClientProps) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<CampaignTab>("overview");
  const [campaignFormOpen, setCampaignFormOpen] = useState(false);
  const [stepFormOpen, setStepFormOpen] = useState(false);
  const [editingStep, setEditingStep] = useState<CampaignSequenceStep | null>(null);
  const [contactSelectOpen, setContactSelectOpen] = useState(false);

  const campaignQuery = useQuery({
    queryFn: () => api.get<Campaign>(`/campaigns/${campaignId}`),
    queryKey: ["campaigns", "detail", campaignId],
  });
  const stepsQuery = useQuery({
    queryFn: () => api.get<CampaignSequenceStep[]>(`/campaigns/${campaignId}/steps`),
    queryKey: ["campaigns", "steps", campaignId],
  });
  const enrollmentsQuery = useQuery({
    queryFn: () => api.get<CampaignEnrollment[]>(`/campaigns/${campaignId}/enrollments`, { page_size: 100 }),
    queryKey: ["campaigns", "enrollments", campaignId],
  });
  const metricsQuery = useQuery({
    queryFn: () => api.get<CampaignMetrics>(`/campaigns/${campaignId}/metrics`),
    queryKey: ["campaigns", "metrics", campaignId],
  });

  const activateCampaign = useMutation({
    mutationFn: () => api.post<Campaign>(`/campaigns/${campaignId}/activate`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "detail", campaignId] });
    },
  });
  const pauseCampaign = useMutation({
    mutationFn: () => api.post<Campaign>(`/campaigns/${campaignId}/pause`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "detail", campaignId] });
    },
  });
  const reorderSteps = useMutation({
    mutationFn: (stepIds: string[]) =>
      api.post<CampaignSequenceStep[], CampaignStepsReorderRequest>(`/campaigns/${campaignId}/steps/reorder`, {
        step_ids: stepIds,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "steps", campaignId] });
    },
  });
  const deleteStep = useMutation({
    mutationFn: (stepId: string) => api.delete<void>(`/campaigns/${campaignId}/steps/${stepId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "steps", campaignId] });
    },
  });
  const unenrollContact = useMutation({
    mutationFn: (contactId: string) => api.delete<CampaignEnrollment>(`/campaigns/${campaignId}/enrollments/${contactId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "enrollments", campaignId] });
    },
  });

  const campaign = campaignQuery.data;
  const steps = stepsQuery.data ?? [];
  const enrollments = enrollmentsQuery.data ?? [];
  const metrics = metricsQuery.data ?? campaign?.metrics;
  const hasMetrics = Boolean(metrics && Object.values(metrics).some((value) => value > 0));
  const hasSteps = steps.length > 0;
  const hasEnrollments = enrollments.length > 0;
  const canActivate = hasSteps && hasEnrollments && campaign?.status !== "active";
  const disabledActivationReason = !hasSteps ? "Add at least one sequence step before activating." : !hasEnrollments ? "Enroll contacts before activating." : "";
  const sortedSteps = [...steps].sort((left, right) => left.step_index - right.step_index);
  const variantComparison = useMemo(() => variantRows(steps), [steps]);

  function onDragEnd(result: DropResult) {
    if (!result.destination || result.destination.index === result.source.index) {
      return;
    }

    const nextSteps = [...sortedSteps];
    const [moved] = nextSteps.splice(result.source.index, 1);
    if (!moved) {
      return;
    }
    nextSteps.splice(result.destination.index, 0, moved);
    reorderSteps.mutate(nextSteps.map((step) => step.id));
  }

  if (campaignQuery.isLoading) {
    return (
      <div className="grid gap-6">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  if (campaignQuery.isError || !campaign) {
    return <div className="rounded-xl border border-red-100 bg-white p-5 text-sm text-red-700 shadow-sm">Could not load campaign.</div>;
  }

  const tabs: Array<{ label: string; value: CampaignTab }> = [
    { label: "Overview", value: "overview" },
    { label: "Sequence", value: "sequence" },
    { label: "Enrollments", value: "enrollments" },
    { label: "Metrics", value: "metrics" },
  ];

  return (
    <div className="grid gap-6">
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-normal text-[#0F2444]">{campaign.name}</h1>
              <StatusPill status={campaign.status} type="campaign" />
              <span className="rounded-full bg-[#EFF6FF] px-2.5 py-1 text-xs font-medium text-[#2563EB]">{optionLabel(campaign.type)}</span>
            </div>
            <p className="mt-2 text-sm text-[#64748B]">
              {formatDate(campaign.start_date)} - {formatDate(campaign.end_date)}
            </p>
          </div>
          <Button onClick={() => setCampaignFormOpen(true)} type="button" variant="outline">
            Edit Campaign
          </Button>
        </div>
      </section>

      <section className="rounded-xl bg-white p-2 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {tabs.map((item) => (
            <button
              className={cn("rounded-md px-4 py-2 text-sm font-semibold", tab === item.value ? "bg-[#2563EB] text-white" : "text-[#64748B] hover:bg-slate-100")}
              key={item.value}
              onClick={() => setTab(item.value)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {tab === "overview" ? (
        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <section className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-[#0F2444]">Campaign Info</h2>
            <dl className="mt-4 grid gap-3 text-sm">
              <div>
                <dt className="text-[#64748B]">Type</dt>
                <dd className="font-semibold text-[#0F2444]">{optionLabel(campaign.type)}</dd>
              </div>
              <div>
                <dt className="text-[#64748B]">Status</dt>
                <dd className="mt-1"><StatusPill status={campaign.status} type="campaign" /></dd>
              </div>
              <div>
                <dt className="text-[#64748B]">Dates</dt>
                <dd className="font-semibold text-[#0F2444]">{formatDate(campaign.start_date)} - {formatDate(campaign.end_date)}</dd>
              </div>
              <div>
                <dt className="text-[#64748B]">Budget</dt>
                <dd className="font-semibold text-[#0F2444]">{formatCurrency(Number(campaign.budget ?? 0))}</dd>
              </div>
            </dl>
            <div className="mt-5">
              {campaign.status === "active" ? (
                <Button disabled={pauseCampaign.isPending} onClick={() => pauseCampaign.mutate()} type="button" variant="outline">
                  <Pause className="h-4 w-4" aria-hidden="true" />
                  Pause
                </Button>
              ) : (
                <div className="inline-flex" title={!canActivate ? disabledActivationReason : undefined}>
                  <Button disabled={!canActivate || activateCampaign.isPending} onClick={() => activateCampaign.mutate()} type="button">
                    <Play className="h-4 w-4" aria-hidden="true" />
                    Activate
                  </Button>
                </div>
              )}
              {!canActivate && campaign.status !== "active" ? <p className="mt-2 text-xs text-amber-700">{disabledActivationReason}</p> : null}
            </div>
          </section>

          <section className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-[#0F2444]">Quick Metrics</h2>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
              {(["sent", "opened", "clicked", "replied", "converted"] as const).map((key) => (
                <div className="rounded-lg bg-[#EFF6FF] p-3" key={key}>
                  <p className="text-xs font-medium text-[#64748B]">{optionLabel(key)}</p>
                  <p className="mt-1 text-2xl font-bold text-[#0F2444]">{metrics?.[key] ?? 0}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {tab === "sequence" ? (
        <section className="rounded-xl bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-[#0F2444]">Email Sequence</h2>
              <p className="mt-1 text-sm text-[#64748B]">Drag steps to reorder. Reorder saves on drop.</p>
            </div>
            <Button onClick={() => { setEditingStep(null); setStepFormOpen(true); }} type="button">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Step
            </Button>
          </div>
          <div className="mt-5">
            {stepsQuery.isLoading ? <Skeleton className="h-72 rounded-xl" /> : null}
            {!stepsQuery.isLoading && sortedSteps.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-[#64748B]">No sequence steps yet.</div> : null}
            <DragDropContext onDragEnd={onDragEnd}>
              <Droppable droppableId="campaign-steps">
                {(provided) => (
                  <div className="grid gap-3" ref={provided.innerRef} {...provided.droppableProps}>
                    {sortedSteps.map((step, index) => (
                      <Draggable draggableId={step.id} index={index} key={step.id}>
                        {(draggableProvided) => {
                          const { style, ...draggableProps } = draggableProvided.draggableProps;

                          return (
                            <article
                              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                              ref={draggableProvided.innerRef}
                              style={style as CSSProperties | undefined}
                              {...draggableProps}
                            >
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                <div className="flex min-w-0 gap-3">
                                  <button className="mt-1 text-[#64748B]" type="button" {...draggableProvided.dragHandleProps}>
                                    <GripVertical className="h-5 w-5" aria-hidden="true" />
                                  </button>
                                  <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <span className="rounded-full bg-[#2563EB] px-2.5 py-1 text-xs font-semibold text-white">Step {index + 1}</span>
                                      <span className="text-xs font-medium text-[#64748B]">Delay: {step.delay_days} days after previous</span>
                                      {step.variant ? <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">Variant {step.variant}</span> : null}
                                    </div>
                                    <h3 className="mt-3 font-semibold text-[#0F2444]">{step.subject}</h3>
                                    <p className="mt-1 text-sm text-slate-700">{preview(step.body)}</p>
                                  </div>
                                </div>
                                <div className="flex gap-2">
                                  <Button onClick={() => { setEditingStep(step); setStepFormOpen(true); }} size="sm" type="button" variant="outline">Edit</Button>
                                  <Button disabled={deleteStep.isPending} onClick={() => deleteStep.mutate(step.id)} size="sm" type="button" variant="ghost">
                                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                                  </Button>
                                </div>
                              </div>
                            </article>
                          );
                        }}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </DragDropContext>
          </div>
        </section>
      ) : null}

      {tab === "enrollments" ? (
        <section className="rounded-xl bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-[#0F2444]">Enrollments</h2>
              <p className="mt-1 text-sm text-[#64748B]">Contacts currently enrolled in this campaign.</p>
            </div>
            <Button onClick={() => setContactSelectOpen(true)} type="button">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Enroll Contacts
            </Button>
          </div>
          <div className="mt-5 overflow-hidden rounded-xl border border-slate-200">
            {enrollments.length === 0 ? <div className="p-8 text-center text-sm text-[#64748B]">No enrolled contacts yet.</div> : null}
            {enrollments.map((enrollment) => (
              <div className="grid gap-3 border-b border-slate-100 px-4 py-3 last:border-b-0 md:grid-cols-[minmax(0,1.4fr)_120px_140px_120px_auto] md:items-center" key={enrollment.id}>
                <div>
                  <Link className="font-semibold text-[#0F2444] hover:text-[#2563EB]" href={`/contacts/${enrollment.contact_id}`}>{enrollment.contact_name ?? "Contact"}</Link>
                  <p className="mt-1 text-xs text-[#64748B]">{enrollment.contact_email}</p>
                </div>
                <span className="text-sm text-[#64748B]">Step {enrollment.step_index + 1}</span>
                <StatusPill status={enrollment.status} type="campaign" />
                <span className="text-sm text-[#64748B]">{formatDate(enrollment.enrolled_at)}</span>
                <Button disabled={unenrollContact.isPending} onClick={() => unenrollContact.mutate(enrollment.contact_id)} size="sm" type="button" variant="outline">
                  Unenroll
                </Button>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {tab === "metrics" ? (
        <section className="rounded-xl bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-[#0F2444]">Metrics</h2>
          {!hasMetrics ? (
            <div className="mt-5 rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-[#64748B]">No data yet</div>
          ) : (
            <>
              <div className="mt-5 h-72">
                <ResponsiveContainer height="100%" width="100%">
                  <LineChart data={metricChartData(metrics)}>
                    <CartesianGrid stroke="#E2E8F0" vertical={false} />
                    <XAxis dataKey="label" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line dataKey="sent" stroke="#2563EB" strokeWidth={2} />
                    <Line dataKey="opened" stroke="#10B981" strokeWidth={2} />
                    <Line dataKey="clicked" stroke="#F59E0B" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-5 grid gap-3 md:grid-cols-4">
                <div className="rounded-lg bg-[#EFF6FF] p-3"><p className="text-xs text-[#64748B]">Open Rate</p><p className="text-xl font-bold text-[#0F2444]">{rate(metrics?.opened ?? 0, metrics?.sent ?? 0)}%</p></div>
                <div className="rounded-lg bg-[#EFF6FF] p-3"><p className="text-xs text-[#64748B]">Click Rate</p><p className="text-xl font-bold text-[#0F2444]">{rate(metrics?.clicked ?? 0, metrics?.sent ?? 0)}%</p></div>
                <div className="rounded-lg bg-[#EFF6FF] p-3"><p className="text-xs text-[#64748B]">Reply Rate</p><p className="text-xl font-bold text-[#0F2444]">{rate(metrics?.replied ?? 0, metrics?.sent ?? 0)}%</p></div>
                <div className="rounded-lg bg-[#EFF6FF] p-3"><p className="text-xs text-[#64748B]">Conversion Rate</p><p className="text-xl font-bold text-[#0F2444]">{rate(metrics?.converted ?? 0, metrics?.sent ?? 0)}%</p></div>
              </div>
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-[#0F2444]">A/B Variant Comparison</h3>
                {variantComparison.length === 0 ? <p className="mt-2 text-sm text-[#64748B]">No variants configured.</p> : null}
                {variantComparison.length > 0 ? (
                  <div className="mt-3 overflow-hidden rounded-xl border border-slate-200">
                    {variantComparison.map((row) => (
                      <div className="grid gap-2 border-b border-slate-100 px-4 py-3 last:border-b-0 md:grid-cols-[120px_120px_minmax(0,1fr)]" key={row.variant}>
                        <span className="font-semibold text-[#0F2444]">Variant {row.variant}</span>
                        <span className="text-sm text-[#64748B]">{row.count} steps</span>
                        <span className="truncate text-sm text-slate-700">{row.subjects.join(", ")}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </>
          )}
        </section>
      ) : null}

      <CampaignForm campaign={campaign} onOpenChange={setCampaignFormOpen} onSaved={() => void campaignQuery.refetch()} open={campaignFormOpen} />
      <SequenceStepForm
        campaignId={campaign.id}
        onOpenChange={(open) => {
          setStepFormOpen(open);
          if (!open) setEditingStep(null);
        }}
        open={stepFormOpen}
        previousStepNumber={editingStep ? Math.max(1, editingStep.step_index) : sortedSteps.length}
        step={editingStep}
      />
      <ContactSelectModal campaignId={campaign.id} onOpenChange={setContactSelectOpen} open={contactSelectOpen} />
    </div>
  );
}
