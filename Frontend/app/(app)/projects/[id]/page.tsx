import { ProjectDetailClient } from "@/components/projects/ProjectDetailClient";

export const dynamic = "force-dynamic";

interface ProjectDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function ProjectDetailPage({ params }: ProjectDetailPageProps) {
  const { id } = await params;
  return <ProjectDetailClient projectId={id} />;
}
