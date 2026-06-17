"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarDays, FolderKanban, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { HealthPill } from "@/components/projects/HealthPill";
import { ProjectForm } from "@/components/projects/ProjectForm";
import { api } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import type { Project, ProjectHealth, User } from "@/types/api";

const healthOptions: ProjectHealth[] = ["green", "yellow", "red"];

function healthLabel(health: ProjectHealth): string {
  if (health === "green") {
    return "On Track";
  }

  if (health === "yellow") {
    return "At Risk";
  }

  return "Delayed";
}

function milestoneStats(project: Project) {
  const total = project.milestones.length;
  const complete = project.milestones.filter((milestone) => milestone.completed_at).length;
  const percent = total > 0 ? Math.round((complete / total) * 100) : 0;

  return { complete, percent, total };
}

export function ProjectsPageClient() {
  const [formOpen, setFormOpen] = useState(false);
  const [health, setHealth] = useState("");
  const [ownerId, setOwnerId] = useState("");

  const projectsQuery = useQuery({
    queryFn: () =>
      api.get<Project[]>("/projects/", {
        health: health || undefined,
        owner_id: ownerId || undefined,
        page_size: 100,
      }),
    queryKey: ["projects", "list", health, ownerId],
  });
  const usersQuery = useQuery({
    queryFn: () => api.get<User[]>("/users/"),
    queryKey: ["users", "project-filters"],
    retry: false,
  });

  const projects = projectsQuery.data ?? [];

  return (
    <div className="grid gap-6">
      <PageHeader
        primaryAction={{ icon: Plus, label: "New Project", onClick: () => setFormOpen(true) }}
        subtitle="Track customer onboarding work, milestones, documents, and portal access."
        title="Projects"
      />

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2">
          <select className="h-10 rounded-md border border-[var(--input)] bg-white px-3 text-sm" onChange={(event) => setHealth(event.target.value)} value={health}>
            <option value="">All health statuses</option>
            {healthOptions.map((option) => (
              <option key={option} value={option}>
                {healthLabel(option)}
              </option>
            ))}
          </select>
          <select className="h-10 rounded-md border border-[var(--input)] bg-white px-3 text-sm" onChange={(event) => setOwnerId(event.target.value)} value={ownerId}>
            <option value="">All owners</option>
            {(usersQuery.data ?? []).map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name}
              </option>
            ))}
          </select>
        </div>
      </section>

      {projectsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((item) => (
            <Skeleton className="h-72 rounded-xl" key={item} />
          ))}
        </div>
      ) : null}

      {!projectsQuery.isLoading && projects.length === 0 && !projectsQuery.isError ? (
        <EmptyState
          action={{ label: "New Project", onClick: () => setFormOpen(true) }}
          description="Create a project manually or convert a closed-won deal into a customer project."
          icon={FolderKanban}
          title="No projects found"
        />
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {projects.map((project) => {
          const stats = milestoneStats(project);

          return (
            <Link className="rounded-xl bg-white p-5 shadow-sm transition hover:shadow-md" href={`/projects/${project.id}`} key={project.id}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold text-[#0F2444]">{project.name}</h2>
                  <p className="mt-1 truncate text-sm text-[#64748B]">{project.account_name ?? "Account"}</p>
                </div>
                <HealthPill health={project.health} />
              </div>

              <div className="mt-5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-[#0F2444]">
                    {stats.complete} of {stats.total} complete
                  </span>
                  <span className="text-[#64748B]">{stats.percent}%</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-[#2563EB]" style={{ width: `${stats.percent}%` }} />
                </div>
              </div>

              <div className="mt-5 grid gap-3 text-sm text-[#64748B]">
                <div className="flex items-center justify-between gap-3">
                  <span>Status</span>
                  <span className="font-medium capitalize text-[#0F2444]">{project.status}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Owner</span>
                  <span className="truncate font-medium text-[#0F2444]">{project.owner_name ?? project.owner_id.slice(0, 8)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4 text-[#2563EB]" aria-hidden="true" />
                  <span>
                    {formatDate(project.start_date)} - {project.end_date ? formatDate(project.end_date) : "No end date"}
                  </span>
                </div>
              </div>

              <div className={cn("mt-5 h-1 rounded-full", project.health === "green" && "bg-emerald-500", project.health === "yellow" && "bg-amber-500", project.health === "red" && "bg-red-500")} />
            </Link>
          );
        })}
      </div>

      {projectsQuery.isError ? <div className="rounded-xl border border-red-100 bg-white p-4 text-sm text-red-700 shadow-sm">Could not load projects.</div> : null}

      <ProjectForm onOpenChange={setFormOpen} open={formOpen} />
    </div>
  );
}
