import { LeadsPageClient } from "@/components/leads/LeadsPageClient";

export const dynamic = "force-dynamic";

interface LeadsPageProps {
  searchParams: Promise<{
    view?: string;
  }>;
}

export default async function LeadsPage({ searchParams }: LeadsPageProps) {
  const { view } = await searchParams;
  return <LeadsPageClient view={view} />;
}
