import { CreditCard } from "lucide-react";

export default function BillingSettingsPage() {
  return (
    <section className="rounded-xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
          <CreditCard className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-xl font-semibold text-[#0F2444]">Billing</h2>
          <p className="mt-1 text-sm text-[#64748B]">Plan, invoice, and workspace billing controls.</p>
        </div>
      </div>
      <div className="mt-6 rounded-lg border border-dashed border-slate-200 p-6 text-sm text-[#64748B]">
        Billing management is available as a placeholder until subscription provider integration is configured.
      </div>
    </section>
  );
}
