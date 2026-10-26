"use client";

import axios from "axios";
import Link from "next/link";
import { ArrowRight, Check, Database, FileText, LockKeyhole, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiUrl } from "../lib/auth-routes";

const capabilities = [
  { icon: Database, title: "Private knowledge bases", text: "Organize internal documents into focused, permissioned sources of truth." },
  { icon: Search, title: "Grounded RAG answers", text: "Retrieve the right context before every response, with citations you can trust." },
  { icon: ShieldCheck, title: "Built-in guardrails", text: "Keep unsafe requests, leakage, and off-topic answers out of the conversation." },
];

export default function HomePage() {
  const router = useRouter();
  const [account, setAccount] = useState<{ full_name: string; email: string } | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    void axios.get<{ full_name: string; email: string }>(`${apiUrl}/auth/me`, { withCredentials: true })
      .then(({ data }) => setAccount(data))
      .catch(() => setAccount(null));
  }, []);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await axios.post(`${apiUrl}/auth/logout`, {}, { withCredentials: true });
      setAccount(null);
      router.replace("/login");
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <main className="klyro-landing">
      <nav className="klyro-nav" aria-label="Primary navigation">
        <Link href="/" className="klyro-logo"><span>K</span> klyro<span className="logo-ai">ai</span></Link>
        <div className="klyro-nav-actions">
          {account ? <>
            <Link href="/dashboard" className="klyro-login-cta">Dashboard</Link>
            <Link href="/dashboard/settings" className="klyro-account-summary" title={account.email}><span>{account.full_name}</span><small>{account.email}</small></Link>
            <button type="button" onClick={() => void handleLogout()} disabled={isLoggingOut} className="klyro-logout-cta">{isLoggingOut ? "Logging out..." : "Log out"}</button>
          </> : <>
            <Link href="/login" className="klyro-login-cta">Log in</Link>
            <Link href="/register" className="klyro-nav-cta">Sign up <ArrowRight size={15} /></Link>
          </>}
        </div>
      </nav>

      <section className="klyro-hero">
        <div className="klyro-hero-copy">
          <p className="klyro-eyebrow"><Sparkles size={14} /> PRIVATE AI, MADE USEFUL</p>
          <h1>Your knowledge.<br /><em>Clear answers.</em></h1>
          <p className="klyro-lede">Klyro AI turns your trusted documents into a private, grounded AI workspace—so your team can ask better questions and move with confidence.</p>
          <div className="klyro-hero-actions">
            <Link href={account ? "/dashboard" : "/register"} className="klyro-primary-cta">{account ? "Open your dashboard" : "Create a private knowledge base"} <ArrowRight size={17} /></Link>
            <a href="#how-it-works" className="klyro-text-cta">See how it works</a>
          </div>
          <div className="klyro-proof"><span><Check size={13} /> Your data stays yours</span><span><Check size={13} /> Citation-first answers</span></div>
        </div>

        <div className="klyro-console" aria-label="Example Klyro AI answer">
          <div className="console-topbar"><span className="console-dot" /><span>Product knowledge base</span><span className="console-status">Protected</span></div>
          <div className="console-body">
            <div className="console-question"><Search size={17} /> What are the enterprise security controls?</div>
            <div className="console-answer"><span className="answer-mark">K</span><div><p>Enterprise workspaces use role-based access, encrypted document storage, and scoped retrieval for every answer.</p><div className="source-pill"><FileText size={13} /> Security overview <span>·</span> 94% match</div></div></div>
          </div>
          <div className="console-footer"><span>Answer grounded in your knowledge</span><ShieldCheck size={16} /></div>
        </div>
      </section>

      <section id="how-it-works" className="klyro-workflow">
        <p className="klyro-eyebrow">ONE TRUSTED FLOW</p>
        <div className="workflow-row">
          <div><span>01</span><h2>Bring your knowledge together.</h2><p>Upload policies, product docs, playbooks, and everything your team already trusts.</p></div>
          <div><span>02</span><h2>Keep it private by design.</h2><p>Create a dedicated knowledge base, with access and context kept within your workspace.</p></div>
          <div><span>03</span><h2>Ask with confidence.</h2><p>Get concise answers grounded in your source material, protected by configurable guardrails.</p></div>
        </div>
      </section>

      <section className="klyro-capabilities">
        <div className="capability-intro"><p className="klyro-eyebrow">BUILT FOR TRUST</p><h2>Less searching.<br />More certainty.</h2><p>Everything you need to make AI genuinely useful across your organization—without giving up control.</p><Link href="/register" className="klyro-inline-link">Build your workspace <ArrowRight size={16} /></Link></div>
        <div className="capability-list">
          {capabilities.map(({ icon: Icon, title, text }) => <article className="capability-card" key={title}><span><Icon size={20} /></span><h3>{title}</h3><p>{text}</p></article>)}
        </div>
      </section>

      <footer className="klyro-footer"><p><LockKeyhole size={14} /> A calm, private space for company knowledge.</p><Link href="/login">Sign in <ArrowRight size={14} /></Link></footer>
    </main>
  );
}
