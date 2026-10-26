"use client";

import axios from "axios";
import { ExternalLink, Globe2, Link2, Loader2, LockKeyhole, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import AccountSettings from "./account-settings";

type KnowledgeBase = { id: string; name: string; description: string; visibility: "private" | "public"; public_share_token: string | null };
const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export default function SettingsPage() {
  const [bases, setBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try { const { data } = await axios.get(`${apiUrl}/knowledge-bases/knowledgebase`, { withCredentials: true }); setBases(data); }
      catch { toast.error("Unable to load knowledge base settings."); }
      finally { setLoading(false); }
    }
    void load();
  }, []);
  async function setVisibility(base: KnowledgeBase, visibility: "private" | "public") {
    setBusy(base.id);
    try {
      const { data } = await axios.patch(`${apiUrl}/knowledge-bases/knowledgebase/${base.id}`, { visibility }, { withCredentials: true });
      setBases((current) => current.map((item) => item.id === base.id ? data : item));
      toast.success(visibility === "public" ? "Knowledge base is now public. Generate a link to share it." : "Knowledge base is now private and its share link has been disabled.");
    } catch { toast.error("Unable to update visibility."); }
    finally { setBusy(null); }
  }
  async function generate(base: KnowledgeBase) {
    setBusy(base.id);
    try {
      const { data } = await axios.post(`${apiUrl}/knowledge-bases/knowledgebase/${base.id}/share-link`, {}, { withCredentials: true });
      setBases((current) => current.map((item) => item.id === base.id ? { ...item, public_share_token: data.public_share_token } : item));
      toast.success("New share link created.");
    } catch (error) { toast.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? "Unable to create a share link." : "Unable to create a share link."); }
    finally { setBusy(null); }
  }
  async function revoke(base: KnowledgeBase) {
    setBusy(base.id);
    try { await axios.delete(`${apiUrl}/knowledge-bases/knowledgebase/${base.id}/share-link`, { withCredentials: true }); setBases((current) => current.map((item) => item.id === base.id ? { ...item, public_share_token: null } : item)); toast.success("Share link revoked."); }
    catch { toast.error("Unable to revoke the share link."); }
    finally { setBusy(null); }
  }
  function shareUrl(token: string) { return `${window.location.origin}/share/${token}`; }
  async function copy(token: string) { await navigator.clipboard.writeText(shareUrl(token)); toast.success("Share link copied."); }

  return <section className="min-w-0"><div className="mb-9"><p className="mb-2 text-[10px] font-semibold tracking-[0.22em] text-[#8172d8]">WORKSPACE / SETTINGS</p><h1 className="text-3xl font-medium tracking-tight sm:text-4xl">Knowledge base access</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-[#6d7484]">Choose which knowledge bases stay private and which can be shared through a secure public chat link.</p></div>
    <div className="mb-6 rounded-2xl border border-[#ddd8f2] bg-[#f3f1ff] p-5 text-sm text-[#5d5b76]"><div className="flex gap-3"><LockKeyhole size={19} className="mt-0.5 shrink-0 text-[#7161d7]" /><p><strong className="text-[#35344c]">Private is the default.</strong> Only people with a public link can chat with a knowledge base you make public. They cannot access your dashboard, documents, or any other knowledge base.</p></div></div>
    {loading ? <div className="flex min-h-44 items-center justify-center rounded-2xl border border-dashed border-[#d6cffa] text-sm text-[#6d7484]"><Loader2 className="mr-2 animate-spin" size={18} /> Loading settings...</div> : <div className="overflow-hidden rounded-2xl border border-[#e8e5de] bg-white"><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-[#e8e5de] bg-[#fcfbf8] text-xs font-medium text-[#6d7484]"><tr><th className="px-5 py-4">Knowledge base</th><th className="px-5 py-4">Visibility</th><th className="px-5 py-4">Public chat link</th><th className="px-5 py-4 text-right">Actions</th></tr></thead><tbody className="divide-y divide-[#f0eee9]">{bases.map((base) => { const isBusy = busy === base.id; const link = base.public_share_token; return <tr key={base.id}><td className="px-5 py-4"><p className="font-medium text-[#273045]">{base.name}</p><p className="mt-1 max-w-xs truncate text-xs text-[#6d7484]">{base.description || "No description"}</p></td><td className="px-5 py-4"><div className="inline-flex rounded-lg border border-[#e8e5de] p-1"><button disabled={isBusy} onClick={() => void setVisibility(base, "private")} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${base.visibility === "private" ? "bg-[#273045] text-white" : "text-[#6d7484]"}`}><LockKeyhole size={13} /> Private</button><button disabled={isBusy} onClick={() => void setVisibility(base, "public")} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${base.visibility === "public" ? "bg-[#7161d7] text-white" : "text-[#6d7484]"}`}><Globe2 size={13} /> Public</button></div></td><td className="px-5 py-4">{base.visibility === "private" ? <span className="text-xs text-[#92939e]">Make public to generate a link</span> : link ? <div className="flex items-center gap-2"><button onClick={() => void copy(link)} className="inline-flex max-w-[165px] items-center gap-1 truncate rounded-lg bg-[#f4f2ff] px-2.5 py-1.5 text-xs font-medium text-[#6658bb]"><Link2 size={13} /> {shareUrl(link)}</button><a href={`/share/${link}`} target="_blank" rel="noreferrer" className="text-[#7161d7]"><ExternalLink size={15} /></a></div> : <span className="text-xs text-[#92939e]">No link yet</span>}</td><td className="px-5 py-4"><div className="flex justify-end gap-2">{base.visibility === "public" && <button disabled={isBusy} onClick={() => void generate(base)} className="inline-flex items-center gap-1.5 rounded-lg border border-[#ddd8f2] px-3 py-2 text-xs font-medium text-[#6658bb] hover:bg-[#f4f2ff]">{link ? <RefreshCw size={13} /> : <Link2 size={13} />}{link ? "Regenerate" : "Generate"}</button>}{link && <button disabled={isBusy} onClick={() => void revoke(base)} aria-label="Revoke share link" className="rounded-lg border border-[#f0d7d2] p-2 text-[#b45a52] hover:bg-[#fff3f0]"><Trash2 size={14} /></button>}</div></td></tr>; })}</tbody></table></div>{bases.length === 0 && <p className="p-8 text-center text-sm text-[#6d7484]">Create a knowledge base first, then control its access here.</p>}</div>}
    <AccountSettings />
  </section>;
}
