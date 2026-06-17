import Link from "next/link";

export default function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#EFF6FF] px-4">
      <section className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-sm">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-[#0F2444] text-lg font-bold text-white">404</div>
        <h1 className="mt-5 text-2xl font-bold text-[#0F2444]">Page not found</h1>
        <p className="mt-3 text-sm leading-6 text-[#64748B]">The page you are looking for does not exist or has moved.</p>
        <Link className="mt-6 inline-flex h-10 items-center justify-center rounded-md bg-[#2563EB] px-4 text-sm font-medium text-white hover:bg-blue-700" href="/dashboard">
          Go to Dashboard
        </Link>
      </section>
    </main>
  );
}
