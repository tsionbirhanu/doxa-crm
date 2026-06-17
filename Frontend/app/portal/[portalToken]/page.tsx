import { format } from "date-fns";
import { notFound } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PortalMilestone {
  title: string;
  due_date: string;
  completed: boolean;
}

interface PortalProject {
  project_name: string;
  account_name: string;
  health: "green" | "yellow" | "red";
  milestones: PortalMilestone[];
  status: string;
  start_date: string;
  end_date: string;
}

async function getPortalProject(portalToken: string): Promise<PortalProject | null> {
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
  const response = await fetch(`${apiUrl}/api/v1/portal/${portalToken}`, {
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error("Could not load portal project");
  }

  return (await response.json()) as PortalProject;
}

export default async function PortalPage({ params }: { params: Promise<{ portalToken: string }> }) {
  const { portalToken } = await params;
  const project = await getPortalProject(portalToken);

  if (!project) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-[#f7f8fb] px-4 py-10">
      <div className="mx-auto grid max-w-3xl gap-6">
        <div>
          <p className="text-sm font-medium uppercase tracking-normal text-[#2f6f73]">{project.account_name}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">{project.project_name}</h1>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Project status</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <PortalStat label="Status" value={project.status} />
            <PortalStat label="Health" value={project.health} />
            <PortalStat label="Timeline" value={`${format(new Date(project.start_date), "MMM d")} - ${format(new Date(project.end_date), "MMM d")}`} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Milestones</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {project.milestones.map((milestone) => (
              <div className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2" key={milestone.title}>
                <div>
                  <p className="text-sm font-medium text-slate-900">{milestone.title}</p>
                  <p className="text-xs text-slate-500">{format(new Date(milestone.due_date), "MMM d, yyyy")}</p>
                </div>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700">
                  {milestone.completed ? "Completed" : "Open"}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

function PortalStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold capitalize text-slate-950">{value}</p>
    </div>
  );
}
