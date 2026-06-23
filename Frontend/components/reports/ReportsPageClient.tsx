"use client";

import { Activity, BarChart3, Handshake, SlidersHorizontal, TrendingUp } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { ActivityTab } from "@/components/reports/ActivityTab";
import { CustomReportBuilder } from "@/components/reports/CustomReportBuilder";
import { CustomersTab } from "@/components/reports/CustomersTab";
import { LeadsTab } from "@/components/reports/LeadsTab";
import { SalesTab } from "@/components/reports/SalesTab";
import { cn } from "@/lib/utils";

type ReportTab = "sales" | "leads" | "activity" | "customers" | "custom";

const tabs = [
  { icon: TrendingUp, id: "sales", label: "Sales" },
  { icon: BarChart3, id: "leads", label: "Leads" },
  { icon: Activity, id: "activity", label: "Activity" },
  { icon: Handshake, id: "customers", label: "Customers" },
  { icon: SlidersHorizontal, id: "custom", label: "Custom" },
] satisfies Array<{ icon: typeof TrendingUp; id: ReportTab; label: string }>;

export function ReportsPageClient() {
  const [activeTab, setActiveTab] = useState<ReportTab>("sales");

  return (
    <div className="grid gap-6">
      <PageHeader subtitle="Analyze pipeline, lead, activity, and customer performance." title="Reports" />

      <section className="rounded-xl bg-white p-2 shadow-sm">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;

            return (
              <button
                className={cn(
                  "inline-flex h-11 items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium transition",
                  active ? "bg-[#2563EB] text-white" : "text-[#64748B] hover:bg-[#EFF6FF] hover:text-[#0F2444]",
                )}
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                type="button"
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {activeTab === "sales" ? <SalesTab /> : null}
      {activeTab === "leads" ? <LeadsTab /> : null}
      {activeTab === "activity" ? <ActivityTab /> : null}
      {activeTab === "customers" ? <CustomersTab /> : null}
      {activeTab === "custom" ? <CustomReportBuilder /> : null}
    </div>
  );
}
