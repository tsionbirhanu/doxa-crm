import { CreditCard } from "lucide-react";

export default function BillingSettingsPage() {
  return (
    <section className="rounded-lg border border-slate-200/70 bg-white p-4 shadow-sm sm:p-6">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
          <CreditCard className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h2 className="text-xl font-semibold text-[#0F2444]">Billing</h2>
          <p className="mt-1 text-sm text-[#64748B]">Plan, invoice, and workspace billing controls.</p>
        </div>
      </div>
      <div className="mt-6 rounded-lg border border-dashed border-slate-200 bg-slate-50/50 p-4 text-sm leading-6 text-[#64748B] sm:p-6">
        Billing management is available as a placeholder until subscription provider integration is configured.
      </div>
    </section>
  );
}
