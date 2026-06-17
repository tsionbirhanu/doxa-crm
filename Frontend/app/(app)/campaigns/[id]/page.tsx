import { CampaignDetailClient } from "@/components/campaigns/CampaignDetailClient";

export const dynamic = "force-dynamic";

interface CampaignDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function CampaignDetailPage({ params }: CampaignDetailPageProps) {
  const { id } = await params;
  return <CampaignDetailClient campaignId={id} />;
}
