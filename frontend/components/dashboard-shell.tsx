"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, FolderOpen, LayoutDashboard, Settings, Sparkles, Globe2, LogOut, Activity } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { apiUrl, loginPath } from "../lib/auth-routes";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/knowledge-base", label: "Knowledge bases", icon: FolderOpen },
  { href: "/dashboard/public-knowledge-bases", label: "Global directory", icon: Globe2 },
  { href: "/dashboard/observability", label: "Observability", icon: Activity },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [isAuthorizing, setIsAuthorizing] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [account, setAccount] = useState<{ full_name: string; email: string } | null>(null);

  useEffect(() => {
    let active = true;

    void axios.get<{ full_name: string; email: string; email_verified_at?: string | null }>(`${apiUrl}/auth/me`, { withCredentials: true })
      .then(({ data }) => {
        if (!active) return;
        if (!data.email_verified_at) {
          router.replace(`/verify-email?next=${encodeURIComponent(pathname)}`);
          return;
        }
        setAccount({ full_name: data.full_name, email: data.email });
        setIsAuthorizing(false);
      })
      .catch(() => {
        if (active) router.replace(loginPath(pathname));
      });

    return () => { active = false; };
  }, [pathname, router]);

  if (isAuthorizing) {
    return <main className="min-h-screen bg-[#fffdf8]" aria-busy="true" />;
  }

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await axios.post(`${apiUrl}/auth/logout`, {}, { withCredentials: true });
      router.replace("/login");
    } catch {
      toast.error("We couldn't sign you out. Please try again.");
      setIsLoggingOut(false);
    }
  }

  const initials = account?.full_name.trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "A";

  return (
    <div className="min-h-screen bg-[#fffdf8] text-[#273045]">
      <header className="sticky top-0 z-40 border-b border-[#e8e5de] bg-[#fffefa]">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#8172d8] text-lg font-semibold text-white">K</span>
            <span className="text-2xl font-semibold tracking-tight">kyro<span className="text-[#8172d8]">.</span></span>
          </Link>
          <div className="flex items-center gap-5 text-sm text-[#6d7484]">
            <Link href="/dashboard" className="hidden items-center gap-1.5 rounded-lg px-2 py-1.5 font-medium transition hover:bg-[#f4f2ff] hover:text-[#8172d8] sm:inline-flex"><LayoutDashboard size={15} /> Dashboard</Link>
            <button
              onClick={() => void handleLogout()}
              disabled={isLoggingOut}
              className="hidden items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition hover:bg-[#fff0ee] hover:text-[#b45a52] disabled:cursor-not-allowed disabled:opacity-60 sm:inline-flex"
            >
              <LogOut size={15} />
              {isLoggingOut ? "Signing out..." : "Sign out"}
            </button>
            <button
              onClick={() => setOpen(true)}
              className="lg:hidden flex h-9 w-9 items-center justify-center rounded-full bg-[#ece8ff] text-[#5a4aa9]"
              aria-label="Open menu"
              aria-expanded={open}
            >
              <Menu size={20} />
            </button>
            <Link href="/dashboard/settings" className="flex items-center gap-2 rounded-full transition hover:bg-[#f4f2ff]" title={account?.email ?? "Account settings"} aria-label="Account settings">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#ece8ff] font-medium text-[#5a4aa9]">{initials}</span>
              <span className="hidden max-w-40 leading-tight lg:block"><strong className="block truncate text-xs font-semibold text-[#3d4255]">{account?.full_name}</strong><small className="block truncate text-[10px] text-[#89909e]">{account?.email}</small></span>
            </Link>
          </div>
        </nav>
      </header>

      <div className="mx-auto grid max-w-7xl gap-10 px-6 py-8 lg:grid-cols-[210px_1fr] lg:px-10 lg:py-12">
        <aside
          className={`fixed top-0 left-0 z-30 h-full w-64 border-r border-[#e8e5de] bg-[#fffefa] p-6 transition-transform duration-300 ease-in-out ${
            open ? "translate-x-0" : "-translate-x-full"
          } lg:sticky lg:top-28 lg:z-auto lg:h-[calc(100vh-8rem)] lg:w-auto lg:self-start lg:translate-x-0 lg:overflow-y-auto lg:border-r-0 lg:p-0`}
        >
          <div className="flex h-full flex-col">
            <p className="mb-4 text-[10px] font-semibold tracking-[0.2em] text-[#9a9ba5]">WORKSPACE</p>
            <div className="space-y-1">
              {navigation.map(({ href, label, icon: Icon, exact }) => {
                const active = exact ? pathname === href : pathname.startsWith(href);
                return (
                  <Link key={href} href={href} onClick={() => setOpen(false)} className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${active ? "bg-[#ece8ff] font-medium text-[#5f51b1]" : "text-[#6d7484] hover:bg-[#ece8ff] hover:text-[#8172d8]"}`}>
                    <Icon size={17} />
                    {label}
                  </Link>
                );
              })}
            </div>
            <div className="mt-auto lg:mt-12 rounded-2xl bg-[#ece8ff] p-4">
              <Sparkles size={19} className="mb-3 text-[#8172d8]" />
              <p className="text-sm font-medium">Knowledge, connected.</p>
              <p className="mt-2 text-xs leading-5 text-[#6d7484]">Your documents. One place. Answers when you need them.</p>
            </div>
            <button
              onClick={() => void handleLogout()}
              disabled={isLoggingOut}
              className="mt-3 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-[#6d7484] transition hover:bg-[#fff0ee] hover:text-[#b45a52] disabled:cursor-not-allowed disabled:opacity-60 sm:hidden"
            >
              <LogOut size={17} />
              {isLoggingOut ? "Signing out..." : "Sign out"}
            </button>
            {open && (
              <button onClick={() => setOpen(false)} className="absolute right-3 top-3 lg:hidden p-1 text-[#6d7484] hover:text-[#8172d8]" aria-label="Close menu">
                <X size={20} />
              </button>
            )}
          </div>
        </aside>
        <main className="min-w-0">{children}</main>
        {open && (
          <div className="fixed inset-0 z-20 bg-black/20 lg:hidden" onClick={() => setOpen(false)} aria-hidden="true" />
        )}
      </div>
    </div>
  );
}
