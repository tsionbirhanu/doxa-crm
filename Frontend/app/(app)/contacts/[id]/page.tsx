import { ContactDetailClient } from "@/components/contacts/ContactDetailClient";

export const dynamic = "force-dynamic";

interface ContactDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function ContactDetailPage({ params }: ContactDetailPageProps) {
  const { id } = await params;
  return <ContactDetailClient contactId={id} />;
}
