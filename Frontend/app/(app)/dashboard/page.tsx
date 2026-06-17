"use client";

import { Activity, ArrowUpRight, BadgeDollarSign, CheckCircle2, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";

const pipelineData = [
  { stage: "Prospecting", value: 42000 },
  { stage: "Qualified", value: 76000 },
  { stage: "Proposal", value: 118000 },
  { stage: "Negotiation", value: 92000 },
  { stage: "Won", value: 54000 },
];

const metrics = [
  { label: "Open deals", value: "128", icon: BadgeDollarSign, tone: "text-[#2f6f73]" },
  { label: "Contacts", value: "2,438", icon: Users, tone: "text-[#0f2a44]" },
  { label: "Activities today", value: "46", icon: Activity, tone: "text-[#8a6b1f]" },
  { label: "Tasks done", value: "31", icon: CheckCircle2, tone: "text-emerald-700" },
] as const;

function formatCurrencyTooltip(value: unknown): [string, string] {
  const numericValue = typeof value === "number" ? value : Number(value ?? 0);
  return [formatCurrency(numericValue), "Value"];
}

export default function DashboardPage() {
  const [chartReady, setChartReady] = useState(false);

  useEffect(() => {
    setChartReady(true);
  }, []);

  return (
    <div className="grid gap-6">
      <PageHeader title="Dashboard" subtitle="Revenue, pipeline, and work queue overview." />
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">{metric.label}</CardTitle>
              <metric.icon className={`h-4 w-4 ${metric.tone}`} aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold text-slate-950">{metric.value}</div>
              <div className="mt-2 flex items-center gap-1 text-xs text-emerald-700">
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                Updated from CRM API
              </div>
            </CardContent>
          </Card>
        ))}
      </section>
      <section className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Pipeline value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              {chartReady ? (
                <ResponsiveContainer height="100%" width="100%">
                  <BarChart data={pipelineData}>
                    <CartesianGrid stroke="#e2e8f0" vertical={false} />
                    <XAxis dataKey="stage" fontSize={12} tickLine={false} />
                    <YAxis fontSize={12} tickFormatter={(value: number) => `$${Math.round(value / 1000)}k`} tickLine={false} />
                    <Tooltip formatter={formatCurrencyTooltip} />
                    <Bar dataKey="value" fill="#2563EB" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full rounded-md bg-slate-50" />
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Today</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {["Review stale deals", "Call top inbound leads", "Approve campaign sequence", "Check overdue tasks"].map((item) => (
              <div className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2" key={item}>
                <span className="text-sm text-slate-700">{item}</span>
                <CheckCircle2 className="h-4 w-4 text-slate-300" aria-hidden="true" />
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
