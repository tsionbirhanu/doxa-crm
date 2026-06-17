import { DealDetailClient } from "@/components/deals/DealDetailClient";

export const dynamic = "force-dynamic";

interface DealDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function DealDetailPage({ params }: DealDetailPageProps) {
  const { id } = await params;
  return <DealDetailClient dealId={id} />;
}
