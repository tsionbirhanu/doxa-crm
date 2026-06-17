import { LeadDetailClient } from "@/components/leads/LeadDetailClient";

export const dynamic = "force-dynamic";

interface LeadDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function LeadDetailPage({ params }: LeadDetailPageProps) {
  const { id } = await params;
  return <LeadDetailClient leadId={id} />;
}
