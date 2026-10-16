"use client";

import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import toast, { Toaster } from "react-hot-toast";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });

  useEffect(() => {
    toast.success("Welcome back — sign in to continue.");
  }, []);

  async function handleLogin() {
    const toastId = toast.loading("Signing you in...");
    try {
      const response = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(form),
      });
      if (!response.ok) {
        const data: { detail?: string } = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? "We couldn’t sign you in. Please try again.");
      }
      toast.success("Login successful!", { id: toastId });
      router.push("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to reach the server. Please try again.", { id: toastId });
    }
  }

  return (
    <main className="auth-page">
      <Toaster position="top-right" toastOptions={{ duration: 3500 }} />
      <Link className="auth-brand" href="/"><span className="wordmark-mark">K</span> kyro</Link>
      <section className="auth-card" aria-labelledby="login-heading">
        <p className="overline">WELCOME BACK</p>
        <h1 id="login-heading">Sign in to Kyro</h1>
        <p className="auth-intro">Your ideas have been waiting for you.</p>

        <form className="auth-form" onSubmit={(event) => { event.preventDefault(); void handleLogin(); }}>
          <label htmlFor="email">Email address</label>
          <input id="email" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />

          <div className="password-label-row"><label htmlFor="password">Password</label><a href="#">Forgot password?</a></div>
          <div className="password-field">
            <input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter your password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required />
            <button className="password-toggle" type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <button type="submit">Sign in</button>
        </form>
        <p className="auth-route-note">New to Kyro? <Link href="/register">Create an account</Link></p>
      </section>
      <p className="auth-bottom">A soft place for serious work.</p>
    </main>
  );
}
