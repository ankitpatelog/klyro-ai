"use client";

import axios from "axios";
import Link from "next/link";
import { Download, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
type Profile = { full_name: string; email: string; email_verified_at?: string | null };
type Usage = { knowledge_base_count: number; document_count: number; storage_bytes: number; chat_request_count: number; rate_limit_per_minute: number };

export default function AccountSettings() {
  const [profile, setProfile] = useState<Profile>({ full_name: "", email: "" });
  const [usage, setUsage] = useState<Usage | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void Promise.all([axios.get(`${apiUrl}/auth/me`, { withCredentials: true }), axios.get(`${apiUrl}/auth/account/usage`, { withCredentials: true })])
      .then(([me, metrics]) => { setProfile(me.data); setUsage(metrics.data); })
      .catch(() => toast.error("Unable to load account settings."));
  }, []);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const response = await axios.patch(`${apiUrl}/auth/account/profile`, profile, { withCredentials: true });
      setProfile((current) => ({ ...current, ...response.data }));
      toast.success(response.data.email_verified_at ? "Profile updated." : "Profile updated. Please verify your email.");
    } catch (error) {
      toast.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? "Unable to update profile." : "Unable to update profile.");
    } finally { setSaving(false); }
  }

  async function danger(endpoint: string, phrase: string) {
    const confirmation = window.prompt(`Type ${phrase} to continue.`);
    if (confirmation !== phrase) return;
    const current_password = window.prompt("Enter your current password to confirm.");
    if (!current_password) return;
    try {
      await axios.delete(`${apiUrl}${endpoint}`, { data: { confirmation, current_password }, withCredentials: true });
      toast.success(endpoint === "/auth/account" ? "Account deleted." : "All knowledge bases were deleted.");
    } catch (error) { toast.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? "Action could not be completed." : "Action could not be completed."); }
  }

  const storage = usage ? `${(usage.storage_bytes / 1024 / 1024).toFixed(2)} MB` : "—";
  const verified = Boolean(profile.email_verified_at);
  return <div className="mt-10 space-y-8">
    <section className="rounded-2xl border border-[#e8e5de] bg-white p-6">
      <div className="mb-5"><p className="text-[10px] font-semibold tracking-[0.2em] text-[#8172d8]">PROFILE</p><h2 className="mt-1 text-xl font-medium">Your account</h2><p className="mt-2 text-sm text-[#6d7484]">Changing your email requires verification before you can upload documents.</p></div>
      <form onSubmit={save} className="grid gap-4 md:grid-cols-2">
        <label className="text-sm">Full name<input value={profile.full_name} onChange={(event) => setProfile({ ...profile, full_name: event.target.value })} className="mt-1.5 w-full rounded-lg border border-[#ddd8f2] px-3 py-2 outline-none focus:border-[#8172d8]" /></label>
        <label className="text-sm">Email<input type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} className="mt-1.5 w-full rounded-lg border border-[#ddd8f2] px-3 py-2 outline-none focus:border-[#8172d8]" /></label>
        <div className={`flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3 text-sm md:col-span-2 ${verified ? "bg-[#e6f4ea] text-[#137333]" : "bg-[#fff0e6] text-[#9a5b2d]"}`}>{verified ? "Email verified — uploads are enabled." : <><span>Email not verified — uploads are disabled.</span><Link href="/verify-email" className="rounded-lg border border-[#8172d8] bg-white px-3 py-2 text-xs font-semibold text-[#7161d7] transition hover:bg-[#f4f2ff]">Verify email</Link></>}</div>
        <button disabled={saving} className="w-fit rounded-lg bg-[#8172d8] px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{saving ? "Saving..." : "Save profile"}</button>
      </form>
    </section>
    <section className="rounded-2xl border border-[#e8e5de] bg-white p-6"><p className="text-[10px] font-semibold tracking-[0.2em] text-[#8172d8]">USAGE</p><h2 className="mt-1 text-xl font-medium">Workspace usage</h2><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[["Storage", storage], ["Documents", usage?.document_count ?? "—"], ["Chat requests", usage?.chat_request_count ?? "—"], ["Rate limit", usage ? `${usage.rate_limit_per_minute}/min` : "—"]].map(([label, value]) => <div key={String(label)} className="rounded-xl bg-[#f7f5ff] p-4"><p className="text-xs text-[#6d7484]">{label}</p><p className="mt-1 text-lg font-medium">{value}</p></div>)}</div></section>
    <section className="rounded-2xl border border-[#f0d7d2] bg-[#fff8f6] p-6"><div className="flex gap-3"><ShieldAlert className="mt-0.5 text-[#b45a52]" size={20} /><div><p className="text-[10px] font-semibold tracking-[0.2em] text-[#b45a52]">DANGER ZONE</p><h2 className="mt-1 text-xl font-medium">Destructive actions</h2><p className="mt-2 text-sm text-[#6d7484]">Export first if you need a copy. Deletions are permanent.</p><div className="mt-5 flex flex-wrap gap-3"><a href={`${apiUrl}/auth/account/export`} className="inline-flex items-center gap-2 rounded-lg border border-[#ddd8f2] bg-white px-4 py-2 text-sm font-medium"><Download size={15} /> Export data</a><button onClick={() => void danger("/auth/account/knowledge-bases", "DELETE BASES")} className="rounded-lg border border-[#e1aaa2] px-4 py-2 text-sm font-medium text-[#a5463f]">Delete all knowledge bases</button><button onClick={() => void danger("/auth/account", "DELETE ACCOUNT")} className="rounded-lg bg-[#a5463f] px-4 py-2 text-sm font-medium text-white">Delete account</button></div></div></div></section>
  </div>;
}
