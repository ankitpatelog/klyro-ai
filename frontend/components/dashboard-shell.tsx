"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  CircleHelp,
  FolderOpen,
  LayoutDashboard,
  Settings2,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/knowledge-base", label: "Knowledge bases", icon: FolderOpen },
  { href: "/dashboard/knowledge-base/", label: "Knowledge bases", icon: FolderOpen },
  { href: "/dashboard/chat", label: "AI playground", icon: Bot },
];

export default function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#fffdf8] text-[#273045]">
      <header className="border-b border-[#e8e5de] bg-[#fffefa]">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#8172d8] text-lg font-semibold text-white">K</span>
            <span className="text-2xl font-semibold tracking-tight">kyro<span className="text-[#8172d8]">.</span></span>
          </Link>
          <div className="flex items-center gap-5 text-sm text-[#6d7484]">
            <Link href="/dashboard" className="hidden transition hover:text-[#8172d8] sm:block">Workspace</Link>
            <Link href="/settings" className="hidden transition hover:text-[#8172d8] sm:block">Settings</Link>
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#ece8ff] font-medium text-[#5a4aa9]">A</span>
          </div>
        </nav>
      </header>

      <div className="mx-auto grid max-w-7xl gap-10 px-6 py-8 lg:grid-cols-[210px_1fr] lg:px-10 lg:py-12">
        <aside className="hidden lg:block">
          <p className="mb-4 text-[10px] font-semibold tracking-[0.2em] text-[#9a9ba5]">WORKSPACE</p>
          <div className="space-y-1">
            {navigation.map(({ href, label, icon: Icon, exact }) => {
              const active = exact ? pathname === href : pathname.startsWith(href);
              return (
                <Link key={href} href={href} className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${active ? "bg-[#ece8ff] font-medium text-[#5f51b1]" : "text-[#6d7484] hover:bg-[#ece8ff] hover:text-[#8172d8]"}`}>
                  <Icon size={17} />
                  {label}
                </Link>
              );
            })}
          </div>
          <div className="mt-10 border-t border-[#e8e5de] pt-5">
            <p className="mb-3 text-[10px] font-semibold tracking-[0.2em] text-[#9a9ba5]">PREFERENCES</p>
            <Link href="/settings" className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-[#6d7484] transition hover:bg-[#ece8ff] hover:text-[#8172d8]"><Settings2 size={17} />Settings</Link>
            <Link href="/help" className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-[#6d7484] transition hover:bg-[#ece8ff] hover:text-[#8172d8]"><CircleHelp size={17} />Help &amp; support</Link>
          </div>
          <div className="mt-12 rounded-2xl bg-[#ece8ff] p-4">
            <Sparkles size={19} className="mb-3 text-[#8172d8]" />
            <p className="text-sm font-medium">Knowledge, connected.</p>
            <p className="mt-2 text-xs leading-5 text-[#6d7484]">Your documents. One place. Answers when you need them.</p>
          </div>
        </aside>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}
