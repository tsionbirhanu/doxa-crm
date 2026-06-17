import { Plug } from "lucide-react";

export default function IntegrationsSettingsPage() {
  return (
    <section className="rounded-xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
          <Plug className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-xl font-semibold text-[#0F2444]">Integrations</h2>
          <p className="mt-1 text-sm text-[#64748B]">Connect email, calendar, storage, and automation tools.</p>
        </div>
      </div>
      <div className="mt-6 rounded-lg border border-dashed border-slate-200 p-6 text-sm text-[#64748B]">
        Integration setup screens are ready to be connected when the backend provider settings are added.
      </div>
    </section>
  );
}
