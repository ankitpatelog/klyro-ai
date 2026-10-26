"use client";

import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import toast, { Toaster } from "react-hot-toast";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setSending(true);
    try { await axios.post(`${apiUrl}/auth/password-reset/request`, { email }); toast.success("If an account exists, a four-digit reset code has been sent."); router.push(`/reset-password?email=${encodeURIComponent(email)}`); }
    catch { toast.error("Unable to request a password reset right now."); }
    finally { setSending(false); }
  }
  return <main className="auth-page"><Toaster position="top-right" /><Link className="auth-brand" href="/"><span className="wordmark-mark">K</span> kyro</Link><section className="auth-card"><p className="overline">PASSWORD RESET</p><h1>Forgot your password?</h1><p className="auth-intro">Enter your email and we’ll send a four-digit reset code.</p><form className="auth-form" onSubmit={submit}><label htmlFor="email">Email address</label><input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required /><button disabled={sending}>{sending ? "Sending code..." : "Send reset code"}</button></form><p className="auth-route-note"><Link href="/login">Back to sign in</Link></p></section><p className="auth-bottom">A soft place for serious work.</p></main>;
}
