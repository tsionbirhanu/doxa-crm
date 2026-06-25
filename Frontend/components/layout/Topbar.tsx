"use client";

import { Bell, Menu, Search } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { SearchModal } from "@/components/search/SearchModal";
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
  const [isMac, setIsMac] = useState(false);
  const { user: storedUser } = useAuthStore();
  const session = authClient.useSession();
  const sessionUser = session.data?.user;
  const pageTitle = useMemo(() => titleFromPath(pathname), [pathname]);
  const name =
    (typeof sessionUser?.full_name === "string" && sessionUser.full_name.trim()) ||
    (typeof sessionUser?.name === "string" && sessionUser.name.trim()) ||
    storedUser?.full_name ||
    "Amina Reed";
  const role = normalizeRole(sessionUser?.role ?? storedUser?.role);
  const displayRole = roleLabel(role);
  const shortcutLabel = isMac ? "⌘ K" : "Ctrl K";

  useEffect(() => {
    setIsMac(/Mac|iPhone|iPad|iPod/i.test(window.navigator.platform));
  }, []);

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      const isSearchShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
      if (!isSearchShortcut) {
        return;
      }

      event.preventDefault();
      setSearchOpen(true);
    }

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-slate-100 bg-white/95 px-4 backdrop-blur md:px-6">
      <nav className="flex h-full items-center justify-between gap-4" aria-label="Primary">
        <div className="flex min-w-0 items-center gap-3">
          <button
            aria-label="Open navigation"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950 md:hidden"
            type="button"
            onClick={onMenuClick}
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
          <ol className="flex min-w-0 items-center gap-1.5 text-xs font-medium text-[#64748B] sm:text-sm">
            <li className="shrink-0">Doxa CRM</li>
            <li className="text-slate-300" aria-hidden="true">
              /
            </li>
            <li className="truncate text-slate-500" aria-current="page">
              {pageTitle}
            </li>
          </ol>
        </div>

        <div className="flex min-w-0 items-center justify-end gap-2 sm:gap-3">
          <button
            className="group hidden h-10 min-w-0 items-center gap-2 rounded-full border border-slate-200/80 bg-slate-50/80 px-3 text-left text-sm text-[#64748B] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] transition-colors hover:border-slate-300 hover:bg-white md:inline-flex md:w-64 lg:w-80"
            onClick={() => setSearchOpen(true)}
            onFocus={() => setSearchOpen(true)}
            type="button"
          >
            <Search className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate">Search</span>
            <kbd className="inline-flex h-6 shrink-0 items-center rounded-md border border-slate-200 bg-white px-2 text-[11px] font-semibold leading-none text-slate-500 shadow-sm">
              {shortcutLabel}
            </kbd>
          </button>

          <button
            aria-label="Search"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950 md:hidden"
            onClick={() => setSearchOpen(true)}
            type="button"
          >
            <Search className="h-5 w-5" aria-hidden="true" />
          </button>

          <button
            aria-label="Notifications"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950"
            type="button"
          >
            <Bell className="h-5 w-5" aria-hidden="true" />
          </button>

          <button
            className="flex h-11 items-center gap-3 rounded-full px-1.5 pl-3 text-left transition-colors hover:bg-slate-100"
            title={`${name} - ${displayRole}`}
            type="button"
          >
            <span className="hidden min-w-0 text-right sm:block">
              <span className="block max-w-36 truncate text-sm font-medium leading-5 text-slate-950">{name}</span>
              <span className="block max-w-36 truncate text-xs leading-4 text-slate-500/80">{displayRole}</span>
            </span>
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/70 bg-gradient-to-br from-blue-50 via-indigo-50 to-emerald-50 text-xs font-semibold text-[#0F2444] shadow-sm ring-1 ring-slate-200/70">
              {getInitials(name)}
            </span>
          </button>
        </div>
      </nav>
      <SearchModal onOpenChange={setSearchOpen} open={searchOpen} />
    </header>
  );
}
