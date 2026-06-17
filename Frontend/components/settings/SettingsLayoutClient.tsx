"use client";

import { CreditCard, Plug, SlidersHorizontal, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { authClient } from "@/lib/auth-client";
import { normalizeRole, type CrmRole } from "@/lib/auth-types";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

interface SettingsLayoutClientProps {
  children: ReactNode;
}

const allowedRoles: CrmRole[] = ["super_admin", "sales_manager"];

const settingsLinks = [
  { href: "/settings/users", icon: Users, label: "Users" },
  { href: "/settings/pipeline", icon: SlidersHorizontal, label: "Pipeline" },
  { disabled: true, href: "/settings/integrations", icon: Plug, label: "Integrations" },
  { disabled: true, href: "/settings/billing", icon: CreditCard, label: "Billing" },
];

export function SettingsLayoutClient({ children }: SettingsLayoutClientProps) {
  const pathname = usePathname();
  const router = useRouter();
  const session = authClient.useSession();
  const storedUser = useAuthStore((state) => state.user);
  const role = normalizeRole(session.data?.user?.role ?? storedUser?.role);
  const isLoading = session.isPending && !storedUser;
  const allowed = allowedRoles.includes(role);

  useEffect(() => {
    if (!isLoading && !allowed) {
      window.sessionStorage.setItem("doxa:last-toast", "Only Super Admins and Sales Managers can access settings.");
      router.replace("/dashboard?settings=unauthorized");
    }
  }, [allowed, isLoading, router]);

  if (isLoading) {
    return <div className="rounded-xl bg-white p-6 text-sm text-[#64748B] shadow-sm">Checking permissions...</div>;
  }

  if (!allowed) {
    return <div className="rounded-xl bg-white p-6 text-sm text-[#64748B] shadow-sm">Redirecting to dashboard...</div>;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
      <aside className="rounded-xl bg-white p-3 shadow-sm">
        <div className="px-3 py-2">
          <h1 className="text-lg font-semibold text-[#0F2444]">Settings</h1>
          <p className="mt-1 text-sm text-[#64748B]">Workspace configuration</p>
        </div>
        <nav className="mt-3 grid gap-1">
          {settingsLinks.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

            if (item.disabled) {
              return (
                <span className="flex h-10 cursor-not-allowed items-center gap-3 rounded-lg px-3 text-sm font-medium text-slate-400" key={item.href}>
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </span>
              );
            }

            return (
              <Link
                className={cn(
                  "flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition",
                  active ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#64748B] hover:bg-slate-50 hover:text-[#0F2444]",
                )}
                href={item.href}
                key={item.href}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
