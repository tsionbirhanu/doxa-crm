"use client";

import { DragDropContext, Draggable, Droppable, type DropResult } from "@hello-pangea/dnd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Pencil, Plus, Save, Trash2 } from "lucide-react";
import { type CSSProperties, useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { PipelineForm } from "@/components/settings/PipelineForm";
import { StageRow } from "@/components/settings/StageRow";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { usePermissions } from "@/lib/permissions";
import { cn } from "@/lib/utils";
import type { Pipeline, PipelineStage, PipelineStageCreate, PipelineStageUpdate, PipelineUpdate } from "@/types/api";

interface AddStageDraft {
  name: string;
  probability: string;
}

function sortStages(stages: PipelineStage[]): PipelineStage[] {
  return [...stages].sort((left, right) => left.order_index - right.order_index);
}

function reorder<T>(items: T[], sourceIndex: number, destinationIndex: number): T[] {
  const next = [...items];
  const [moved] = next.splice(sourceIndex, 1);
  if (!moved) {
    return items;
  }

  next.splice(destinationIndex, 0, moved);
  return next;
}

export function PipelineSettingsClient() {
  const queryClient = useQueryClient();
  const { canAdminPipeline } = usePermissions();
  const [formOpen, setFormOpen] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [editingPipelineId, setEditingPipelineId] = useState<string | null>(null);
  const [pipelineNameDraft, setPipelineNameDraft] = useState("");
  const [addingPipelineId, setAddingPipelineId] = useState<string | null>(null);
  const [addDraft, setAddDraft] = useState<AddStageDraft>({ name: "", probability: "10" });
  const [pipelineToDelete, setPipelineToDelete] = useState<Pipeline | null>(null);

  const pipelinesQuery = useQuery({
    queryFn: () => api.get<Pipeline[]>("/pipelines/"),
    queryKey: ["pipelines", "settings"],
  });

  useEffect(() => {
    const nextPipelines = (pipelinesQuery.data ?? []).map((pipeline) => ({
      ...pipeline,
      stages: sortStages(pipeline.stages),
    }));
    setPipelines(nextPipelines);
    if (nextPipelines.length > 0 && expanded.size === 0) {
      setExpanded(new Set([nextPipelines[0].id]));
    }
  }, [expanded.size, pipelinesQuery.data]);

  const updatePipeline = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PipelineUpdate }) => api.patch<Pipeline, PipelineUpdate>(`/pipelines/${id}`, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["pipelines"] }),
  });

  const deletePipeline = useMutation({
    mutationFn: (id: string) => api.delete<void>(`/pipelines/${id}`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["pipelines"] }),
  });

  const addStage = useMutation({
    mutationFn: ({ pipeline, payload }: { pipeline: Pipeline; payload: PipelineStageCreate }) =>
      api.post<PipelineStage, PipelineStageCreate>(`/pipelines/${pipeline.id}/stages`, payload),
    onSuccess: () => {
      setAddingPipelineId(null);
      setAddDraft({ name: "", probability: "10" });
      void queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
  });

  const reorderStages = useMutation({
    mutationFn: ({ pipelineId, stages }: { pipelineId: string; stages: PipelineStage[] }) =>
      Promise.all(
        stages.map((stage, index) =>
          api.patch<PipelineStage, PipelineStageUpdate>(`/pipelines/${pipelineId}/stages/${stage.id}`, {
            order_index: index,
          }),
        ),
      ),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["pipelines"] }),
  });

  const pipelinesById = useMemo(() => new Map(pipelines.map((pipeline) => [pipeline.id, pipeline])), [pipelines]);

  function toggleExpanded(pipelineId: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(pipelineId)) {
        next.delete(pipelineId);
      } else {
        next.add(pipelineId);
      }
      return next;
    });
  }

  function beginPipelineEdit(pipeline: Pipeline) {
    if (!canAdminPipeline) {
      return;
    }

    setEditingPipelineId(pipeline.id);
    setPipelineNameDraft(pipeline.name);
  }

  function savePipelineName(pipeline: Pipeline) {
    if (!canAdminPipeline) {
      return;
    }

    const nextName = pipelineNameDraft.trim();
    setEditingPipelineId(null);
    if (!nextName || nextName === pipeline.name) {
      setPipelineNameDraft("");
      return;
    }

    updatePipeline.mutate({ id: pipeline.id, payload: { name: nextName } });
  }

  function deletePipelineIfAllowed(pipeline: Pipeline) {
    if (!canAdminPipeline) {
      return;
    }

    if (pipeline.is_default) {
      return;
    }

    setPipelineToDelete(pipeline);
  }

  function showAddStage(pipelineId: string) {
    if (!canAdminPipeline) {
      return;
    }

    setAddingPipelineId(pipelineId);
    setAddDraft({ name: "", probability: "10" });
  }

  function saveNewStage(pipeline: Pipeline) {
    if (!canAdminPipeline) {
      return;
    }

    const probability = Number(addDraft.probability);
    if (!addDraft.name.trim() || Number.isNaN(probability) || probability < 0 || probability > 100) {
      return;
    }

    addStage.mutate({
      pipeline,
      payload: {
        name: addDraft.name.trim(),
        order_index: pipeline.stages.length,
        probability,
      },
    });
  }

  function onDragEnd(result: DropResult) {
    if (!canAdminPipeline) {
      return;
    }

    if (!result.destination) {
      return;
    }

    const pipelineId = result.source.droppableId;
    if (pipelineId !== result.destination.droppableId || result.source.index === result.destination.index) {
      return;
    }

    const pipeline = pipelinesById.get(pipelineId);
    if (!pipeline) {
      return;
    }

    const previous = pipelines;
    const reorderedStages = reorder(pipeline.stages, result.source.index, result.destination.index).map((stage, index) => ({
      ...stage,
      order_index: index,
    }));
    setPipelines((current) => current.map((item) => (item.id === pipelineId ? { ...item, stages: reorderedStages } : item)));

    reorderStages.mutate(
      { pipelineId, stages: reorderedStages },
      {
        onError: () => setPipelines(previous),
      },
    );
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        primaryAction={canAdminPipeline ? { icon: Plus, label: "New Pipeline", onClick: () => setFormOpen(true) } : undefined}
        subtitle="Configure sales pipelines, stage probabilities, and stage order."
        title="Pipeline Settings"
      />

      {pipelinesQuery.isLoading ? <div className="rounded-xl bg-white p-6 text-sm text-[#64748B] shadow-sm">Loading pipelines...</div> : null}
      {pipelinesQuery.isError ? <div className="rounded-xl border border-red-100 bg-white p-4 text-sm text-red-700 shadow-sm">Could not load pipelines.</div> : null}

      <DragDropContext onDragEnd={onDragEnd}>
        <div className="grid gap-4">
          {pipelines.map((pipeline) => {
            const isExpanded = expanded.has(pipeline.id);
            const editing = editingPipelineId === pipeline.id;

            return (
              <section className="overflow-hidden rounded-xl bg-white shadow-sm" key={pipeline.id}>
                <header className="flex flex-col gap-3 border-b border-slate-200 p-4 md:flex-row md:items-center md:justify-between">
                  <div className="flex min-w-0 items-center gap-3">
                    <button
                      aria-label={isExpanded ? "Collapse pipeline" : "Expand pipeline"}
                      className="grid h-8 w-8 place-items-center rounded-md text-[#64748B] hover:bg-slate-100"
                      onClick={() => toggleExpanded(pipeline.id)}
                      type="button"
                    >
                      {isExpanded ? <ChevronDown className="h-4 w-4" aria-hidden="true" /> : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
                    </button>
                    {editing ? (
                      <Input
                        autoFocus
                        className="max-w-sm"
                        onBlur={() => savePipelineName(pipeline)}
                        onChange={(event) => setPipelineNameDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.currentTarget.blur();
                          }
                          if (event.key === "Escape") {
                            setEditingPipelineId(null);
                          }
                        }}
                        value={pipelineNameDraft}
                      />
                    ) : (
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h2 className="truncate text-lg font-semibold text-[#0F2444]">{pipeline.name}</h2>
                          {pipeline.is_default ? (
                            <span className="rounded-full bg-[#EFF6FF] px-2.5 py-1 text-xs font-semibold text-[#2563EB]">Default</span>
                          ) : null}
                        </div>
                        <p className="mt-1 text-sm text-[#64748B]">{pipeline.stages.length} stages</p>
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {canAdminPipeline ? (
                      <>
                        <Button onClick={() => beginPipelineEdit(pipeline)} size="sm" type="button" variant="outline">
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                          Edit Name
                        </Button>
                        <Button
                          disabled={pipeline.is_default || deletePipeline.isPending}
                          onClick={() => deletePipelineIfAllowed(pipeline)}
                          size="sm"
                          title={pipeline.is_default ? "Default pipeline cannot be deleted." : "Delete pipeline"}
                          type="button"
                          variant="outline"
                        >
                          <Trash2 className="h-4 w-4 text-red-600" aria-hidden="true" />
                          Delete
                        </Button>
                      </>
                    ) : null}
                  </div>
                </header>

                {isExpanded ? (
                  <div className="grid gap-3 p-4">
                    <Droppable droppableId={pipeline.id} isDropDisabled={!canAdminPipeline}>
                      {(provided) => (
                        <div className="grid gap-3" ref={provided.innerRef} {...provided.droppableProps}>
                          {pipeline.stages.map((stage, index) => (
                            <Draggable draggableId={stage.id} index={index} isDragDisabled={!canAdminPipeline} key={stage.id}>
                              {(draggableProvided, snapshot) => {
                                const { style, ...draggableProps } = draggableProvided.draggableProps;

                                return (
                                  <div
                                    className={cn(snapshot.isDragging && "opacity-90")}
                                    ref={draggableProvided.innerRef}
                                    style={style as CSSProperties | undefined}
                                    {...draggableProps}
                                  >
                                    <StageRow canEdit={canAdminPipeline} dragHandleProps={draggableProvided.dragHandleProps} pipelineId={pipeline.id} stage={stage} />
                                  </div>
                                );
                              }}
                            </Draggable>
                          ))}
                          {provided.placeholder}
                        </div>
                      )}
                    </Droppable>

                    {canAdminPipeline && addingPipelineId === pipeline.id ? (
                      <div className="grid gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3 md:grid-cols-[1fr_140px_auto_auto]">
                        <Input
                          aria-label="New stage name"
                          onChange={(event) => setAddDraft((current) => ({ ...current, name: event.target.value }))}
                          placeholder="Stage name"
                          value={addDraft.name}
                        />
                        <Input
                          aria-label="New stage probability"
                          max="100"
                          min="0"
                          onChange={(event) => setAddDraft((current) => ({ ...current, probability: event.target.value }))}
                          type="number"
                          value={addDraft.probability}
                        />
                        <Button disabled={addStage.isPending} onClick={() => saveNewStage(pipeline)} type="button">
                          <Save className="h-4 w-4" aria-hidden="true" />
                          Save
                        </Button>
                        <Button onClick={() => setAddingPipelineId(null)} type="button" variant="outline">
                          Cancel
                        </Button>
                      </div>
                    ) : canAdminPipeline ? (
                      <Button className="justify-self-start" onClick={() => showAddStage(pipeline.id)} type="button" variant="outline">
                        <Plus className="h-4 w-4" aria-hidden="true" />
                        Add Stage
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      </DragDropContext>

      {canAdminPipeline ? (
        <>
          <PipelineForm onOpenChange={setFormOpen} open={formOpen} />
          <ConfirmDialog
            isPending={deletePipeline.isPending}
            onConfirm={() => {
              if (pipelineToDelete) {
                deletePipeline.mutate(pipelineToDelete.id, {
                  onSuccess: () => setPipelineToDelete(null),
                });
              }
            }}
            onOpenChange={(open) => {
              if (!open) {
                setPipelineToDelete(null);
              }
            }}
            open={Boolean(pipelineToDelete)}
            title="Delete pipeline"
          />
        </>
      ) : null}
    </div>
  );
}
