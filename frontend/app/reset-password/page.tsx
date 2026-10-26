"use client";

import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import toast, { Toaster } from "react-hot-toast";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export default function ResetPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState(""); const [password, setPassword] = useState(""); const [saving, setSaving] = useState(false);
  useEffect(() => { setEmail(new URLSearchParams(window.location.search).get("email") ?? ""); }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setSaving(true);
    try { await axios.post(`${apiUrl}/auth/password-reset/confirm`, { email, code, new_password: password }); toast.success("Password changed. Please sign in."); router.push("/login"); }
    catch (error) { toast.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? "Unable to reset password." : "Unable to reset password."); }
    finally { setSaving(false); }
  }
  return <main className="auth-page"><Toaster position="top-right" /><Link className="auth-brand" href="/"><span className="wordmark-mark">K</span> kyro</Link><section className="auth-card"><p className="overline">CHOOSE A NEW PASSWORD</p><h1>Reset password</h1><p className="auth-intro">Enter the code from your email, then choose a new password.</p><form className="auth-form" onSubmit={submit}><label htmlFor="email">Email address</label><input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /><label htmlFor="code">Four-digit code</label><input id="code" inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 4))} placeholder="0000" required /><label htmlFor="password">New password</label><input id="password" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required /><button disabled={saving || code.length !== 4}>{saving ? "Changing password..." : "Change password"}</button></form><p className="auth-route-note"><Link href="/forgot-password">Request a new code</Link></p></section><p className="auth-bottom">A soft place for serious work.</p></main>;
}
