"use client";

import { Bell, Menu, Search, UserCircle } from "lucide-react";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { authClient } from "@/lib/auth-client";
import { normalizeRole } from "@/lib/auth-types";
import { getInitials } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

interface TopbarProps {
  onMenuClick: () => void;
}

function titleFromPath(pathname: string): string {
  const firstSegment = pathname.split("/").filter(Boolean)[0] ?? "dashboard";

  return firstSegment
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function roleLabel(role: string): string {
  return role
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);
  const { user: storedUser } = useAuthStore();
  const session = authClient.useSession();
  const sessionUser = session.data?.user;
  const pageTitle = useMemo(() => titleFromPath(pathname), [pathname]);
  const name =
    (typeof sessionUser?.full_name === "string" && sessionUser.full_name.trim()) ||
    (typeof sessionUser?.name === "string" && sessionUser.name.trim()) ||
    storedUser?.full_name ||
    "Doxa User";
  const role = normalizeRole(sessionUser?.role ?? storedUser?.role);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          aria-label="Open navigation"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100 md:hidden"
          type="button"
          onClick={onMenuClick}
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-950">{pageTitle}</div>
          <div className="hidden text-xs text-[#64748B] sm:block">Doxa CRM / {pageTitle}</div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
          <DialogTrigger asChild>
            <button
              className="hidden h-9 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm text-[#64748B] hover:bg-slate-50 sm:inline-flex"
              type="button"
            >
              <Search className="h-4 w-4" aria-hidden="true" />
              Search
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Global search</DialogTitle>
              <DialogDescription>Search contacts, accounts, deals, and leads from one place.</DialogDescription>
            </DialogHeader>
            <div className="flex h-11 items-center gap-2 rounded-md border border-slate-200 px-3 text-sm text-[#64748B]">
              <Search className="h-4 w-4" aria-hidden="true" />
              <span>Search modal ready for the global search API.</span>
            </div>
          </DialogContent>
        </Dialog>

        <button
          aria-label="Notifications"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100"
          type="button"
        >
          <Bell className="h-5 w-5" aria-hidden="true" />
        </button>

        <button
          className="flex h-9 items-center gap-2 rounded-md px-2 text-left hover:bg-slate-100"
          title={`${name} - ${roleLabel(role)}`}
          type="button"
        >
          <span className="hidden min-w-0 text-right sm:block">
            <span className="block max-w-32 truncate text-xs font-semibold text-slate-950">{name}</span>
            <span className="block max-w-32 truncate text-[11px] text-[#64748B]">{roleLabel(role)}</span>
          </span>
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#EFF6FF] text-xs font-semibold text-[#2563EB]">
            {name ? getInitials(name) : <UserCircle className="h-5 w-5" aria-hidden="true" />}
          </span>
        </button>
      </div>
    </header>
  );
}
