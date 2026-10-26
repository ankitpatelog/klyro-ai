"use client";

import axios from "axios";
import { Activity, Coins, Database, Gauge, Layers3, RefreshCw, Timer } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiUrl } from "../../../lib/auth-routes";

type Metrics = {
  window_days: number;
  request_count: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  average_latency_ms: number;
  cache_hit_rate: number;
  average_retrieved_chunks: number;
  models: { model: string; requests: number }[];
};

const number = new Intl.NumberFormat("en-US");

export default function ObservabilityPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const load = useCallback(() => axios
    .get<Metrics>(`${apiUrl}/rag/observability`, { params: { days }, withCredentials: true })
    .then(({ data }) => setMetrics(data))
    .finally(() => setLoading(false)), [days]);

  useEffect(() => { void load(); }, [load]);

  const cards = metrics ? [
    { label: "RAG requests", value: number.format(metrics.request_count), icon: Activity },
    { label: "Tokens processed", value: number.format(metrics.total_tokens), icon: Database },
    { label: "Avg. latency", value: `${number.format(metrics.average_latency_ms)} ms`, icon: Timer },
    { label: "Cache-hit rate", value: `${metrics.cache_hit_rate}%`, icon: Gauge },
    { label: "Retrieved chunks", value: metrics.average_retrieved_chunks.toFixed(1), icon: Layers3 },
    { label: "Estimated cost", value: `$${metrics.estimated_cost_usd.toFixed(4)}`, icon: Coins },
  ] : [];

  return (
    <section className="space-y-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-sm font-medium text-[#8172d8]">RAG performance</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Observability</h1><p className="mt-2 text-sm text-[#6d7484]">Measure the optimizations applied to your knowledge-base answers.</p></div>
        <div className="flex gap-2"><select value={days} onChange={(event) => { setLoading(true); setDays(Number(event.target.value)); }} className="rounded-xl border border-[#e8e5de] bg-white px-3 py-2 text-sm"><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option></select><button onClick={() => { setLoading(true); void load(); }} disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-[#7161d7] px-3 py-2 text-sm font-medium text-white disabled:opacity-60"><RefreshCw size={15} className={loading ? "animate-spin" : ""} /> Refresh</button></div>
      </div>

      {loading && !metrics ? <div className="rounded-2xl border border-dashed border-[#d6cffa] p-12 text-center text-sm text-[#6d7484]">Loading RAG metrics…</div> : <>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{cards.map(({ label, value, icon: Icon }) => <div key={label} className="rounded-2xl border border-[#e8e5de] bg-white p-5"><Icon size={19} className="text-[#8172d8]" /><p className="mt-4 text-xs font-medium uppercase tracking-wide text-[#8b8e9a]">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p></div>)}</div>
        <div className="grid gap-4 lg:grid-cols-2"><div className="rounded-2xl border border-[#e8e5de] bg-white p-5"><h2 className="font-semibold">Token usage</h2><div className="mt-5 space-y-3 text-sm"><div className="flex justify-between"><span className="text-[#6d7484]">Input tokens</span><span>{number.format(metrics?.input_tokens ?? 0)}</span></div><div className="flex justify-between"><span className="text-[#6d7484]">Output tokens</span><span>{number.format(metrics?.output_tokens ?? 0)}</span></div></div></div><div className="rounded-2xl border border-[#e8e5de] bg-white p-5"><h2 className="font-semibold">Model usage</h2><div className="mt-4 space-y-3">{metrics?.models.length ? metrics.models.map((item) => <div key={item.model} className="flex justify-between gap-4 text-sm"><span className="truncate text-[#6d7484]">{item.model}</span><span>{number.format(item.requests)} requests</span></div>) : <p className="text-sm text-[#6d7484]">No RAG requests in this period.</p>}</div></div></div>
        <p className="text-xs text-[#8b8e9a]">Cost is an estimate based on the optional backend token-pricing settings. Cached answers do not call the generation model.</p>
      </>}
    </section>
  );
}
