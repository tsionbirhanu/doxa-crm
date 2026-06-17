import { AccountDetailClient } from "@/components/accounts/AccountDetailClient";

export const dynamic = "force-dynamic";

interface AccountDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function AccountDetailPage({ params }: AccountDetailPageProps) {
  const { id } = await params;
  return <AccountDetailClient accountId={id} />;
}
