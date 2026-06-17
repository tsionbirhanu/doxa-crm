"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { CampaignEnrollRequest, CampaignEnrollment, Contact } from "@/types/api";

interface ContactSelectModalProps {
  campaignId: string;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timeoutId);
  }, [delayMs, value]);

  return debounced;
}

function contactName(contact: Contact): string {
  return `${contact.first_name} ${contact.last_name}`;
}

export function ContactSelectModal({ campaignId, onOpenChange, open }: ContactSelectModalProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const debouncedSearch = useDebouncedValue(search, 300);
  const contactsQuery = useQuery({
    enabled: open,
    queryFn: () => api.get<Contact[]>("/contacts/", { page_size: 50, search: debouncedSearch || undefined }),
    queryKey: ["campaigns", "contact-select", debouncedSearch],
  });
  const contacts = useMemo(() => {
    const normalized = debouncedSearch.toLowerCase();
    return (contactsQuery.data ?? []).filter((contact) => `${contactName(contact)} ${contact.email}`.toLowerCase().includes(normalized));
  }, [contactsQuery.data, debouncedSearch]);
  const enrollContacts = useMutation({
    mutationFn: () =>
      api.post<CampaignEnrollment[], CampaignEnrollRequest>(`/campaigns/${campaignId}/enroll`, {
        contact_ids: Array.from(selectedIds),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "enrollments", campaignId] });
      setSelectedIds(new Set());
      onOpenChange(false);
    },
  });

  function toggleContact(contactId: string, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(contactId);
      } else {
        next.delete(contactId);
      }
      return next;
    });
  }

  return (
    <Dialog
      onOpenChange={(nextOpen) => {
        onOpenChange(nextOpen);
        if (!nextOpen) {
          setSelectedIds(new Set());
          setSearch("");
        }
      }}
      open={open}
    >
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Enroll Contacts</DialogTitle>
          <DialogDescription>Search contacts and enroll selected people into this campaign.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]" aria-hidden="true" />
            <Input className="pl-9" onChange={(event) => setSearch(event.target.value)} placeholder="Search contacts" value={search} />
          </div>
          <div className="flex items-center justify-between">
            <span className="rounded-full bg-[#EFF6FF] px-3 py-1 text-sm font-semibold text-[#2563EB]">{selectedIds.size} selected</span>
          </div>
          <div className="max-h-80 overflow-y-auto rounded-xl border border-slate-200">
            {contactsQuery.isLoading ? <div className="p-4 text-sm text-[#64748B]">Loading contacts...</div> : null}
            {!contactsQuery.isLoading && contacts.length === 0 ? <div className="p-4 text-sm text-[#64748B]">No contacts found.</div> : null}
            {contacts.map((contact) => (
              <label className="flex cursor-pointer items-center gap-3 border-b border-slate-100 px-4 py-3 last:border-b-0 hover:bg-[#EFF6FF]" key={contact.id}>
                <input
                  checked={selectedIds.has(contact.id)}
                  className="h-4 w-4 rounded border-slate-300"
                  onChange={(event) => toggleContact(contact.id, event.target.checked)}
                  type="checkbox"
                />
                <div>
                  <p className="text-sm font-semibold text-[#0F2444]">{contactName(contact)}</p>
                  <p className="text-xs text-[#64748B]">{contact.email}</p>
                </div>
              </label>
            ))}
          </div>
          {enrollContacts.isError ? <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Could not enroll contacts.</div> : null}
          <div className="flex justify-end gap-3">
            <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
              Cancel
            </Button>
            <Button
              className="bg-[#2563EB] hover:bg-blue-700"
              disabled={selectedIds.size === 0 || enrollContacts.isPending}
              onClick={() => enrollContacts.mutate()}
              type="button"
            >
              Enroll {selectedIds.size} contacts
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
