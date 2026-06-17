import { PageHeader } from "@/components/layout/PageHeader";
import { SearchPageClient } from "@/components/search/SearchPageClient";

export default function SearchPage() {
  return (
    <div className="grid gap-6">
      <PageHeader subtitle="Search contacts, accounts, deals, and leads across the CRM." title="Search" />
      <SearchPageClient />
    </div>
  );
}
