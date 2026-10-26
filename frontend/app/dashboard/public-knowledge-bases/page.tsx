"use client";

import axios from "axios";
import Link from "next/link";
import { ExternalLink, FileText, Globe2, Loader2, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

type PublicKnowledgeBase = {
  id: string;
  name: string;
  description: string;
  author_name: string;
  public_share_token: string;
  document_count: number;
  created_at: string;
};

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export default function PublicKnowledgeBasesPage() {
  const [bases, setBases] = useState<PublicKnowledgeBase[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await axios.get<PublicKnowledgeBase[]>(`${apiUrl}/knowledge-bases/public`);
        setBases(data);
      } catch {
        toast.error("Unable to load public knowledge bases.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  const matches = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return bases;
    return bases.filter((base) => `${base.name} ${base.description}`.toLowerCase().includes(term));
  }, [bases, query]);

  return (
    <section className="min-w-0">
      <div className="mb-9">
        <p className="mb-2 text-[10px] font-semibold tracking-[0.22em] text-[#8172d8]">DISCOVER / PUBLIC KNOWLEDGE</p>
        <h1 className="text-3xl font-medium tracking-tight sm:text-4xl">Public knowledge bases</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6d7484]">Search published knowledge bases and open their existing public conversation links.</p>
      </div>

      <label className="mb-6 flex items-center gap-3 rounded-2xl border border-[#ddd8f2] bg-white px-4 py-3 shadow-sm focus-within:border-[#8172d8]" htmlFor="public-base-search">
        <Search size={18} className="text-[#8172d8]" />
        <input id="public-base-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search public knowledge bases..." className="w-full bg-transparent text-sm outline-none placeholder:text-[#9a9ba5]" />
      </label>

      {loading ? (
        <div className="flex min-h-44 items-center justify-center rounded-2xl border border-dashed border-[#d6cffa] text-sm text-[#6d7484]"><Loader2 className="mr-2 animate-spin" size={18} /> Loading public knowledge bases...</div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-[#e8e5de] bg-white">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="border-b border-[#e8e5de] bg-[#fcfbf8] text-xs font-medium text-[#6d7484]"><tr><th className="px-5 py-4">Knowledge base</th><th className="px-5 py-4">Publisher</th><th className="px-5 py-4">Documents</th><th className="px-5 py-4">Published</th><th className="px-5 py-4 text-right">Conversation</th></tr></thead>
              <tbody className="divide-y divide-[#f0eee9]">
                {matches.map((base) => <tr key={base.id} className="hover:bg-[#fcfbf8]"><td className="px-5 py-4"><div className="flex items-start gap-3"><span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#ece8ff] text-[#7161d7]"><Globe2 size={16} /></span><div><p className="font-medium text-[#273045]">{base.name}</p><p className="mt-1 max-w-md text-xs leading-5 text-[#6d7484]">{base.description || "No description provided."}</p></div></div></td><td className="px-5 py-4 text-[#6d7484]">{base.author_name}</td><td className="px-5 py-4 text-[#6d7484]"><span className="inline-flex items-center gap-1.5"><FileText size={14} /> {base.document_count}</span></td><td className="px-5 py-4 text-xs text-[#6d7484]">{new Date(base.created_at).toLocaleDateString()}</td><td className="px-5 py-4 text-right"><Link href={`/share/${base.public_share_token}`} className="inline-flex items-center gap-1.5 rounded-lg bg-[#8172d8] px-3 py-2 text-xs font-medium text-white transition hover:bg-[#6f60c5]">Open chat <ExternalLink size={13} /></Link></td></tr>)}
              </tbody>
            </table>
          </div>
          {matches.length === 0 && <div className="p-10 text-center text-sm text-[#6d7484]">{bases.length === 0 ? "No public knowledge bases are available yet." : "No public knowledge bases match your search."}</div>}
        </div>
      )}
    </section>
  );
}
