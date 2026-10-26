import Link from "next/link";
import { ArrowLeft, Compass, Home } from "lucide-react";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#fffdf8] px-6 py-16 text-[#273045]">
      <section className="w-full max-w-xl rounded-3xl border border-[#e8e5de] bg-white p-8 text-center shadow-sm sm:p-12">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#ece8ff] text-[#6658bb]">
          <Compass size={28} aria-hidden="true" />
        </div>
        <p className="mt-7 text-sm font-semibold tracking-[0.18em] text-[#8172d8]">ERROR 404</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">This page does not exist.</h1>
        <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-[#6d7484]">The link may be outdated, or the address may have been entered incorrectly. Let’s get you back to your knowledge workspace.</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/" className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#7161d7] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#6658bb]"><Home size={16} /> Go to home</Link>
          <Link href="/dashboard" className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#ddd8f2] px-4 py-2.5 text-sm font-medium text-[#6658bb] transition hover:bg-[#f4f2ff]"><ArrowLeft size={16} /> Open dashboard</Link>
        </div>
      </section>
    </main>
  );
}
