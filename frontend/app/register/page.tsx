"use client";

import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import toast, { Toaster } from "react-hot-toast";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ fullName: "", email: "", password: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    toast("Create your Kyro workspace account.", { icon: "✨" });
  }, []);

  async function handleRegister() {
    setIsSubmitting(true);
    const toastId = toast.loading("Creating your account...");

    try {
      await axios.post(`${apiUrl}/auth/register`, {
        full_name: form.fullName,
        email: form.email,
        password: form.password,
      });
      toast.success("Account created! You can sign in now.", { id: toastId });
      router.push("/");
    } catch (error) {
      const message = axios.isAxiosError<{ detail?: string }>(error)
        ? error.response?.data.detail ?? "We couldn’t create your account. Please try again."
        : "Unable to reach the server. Please try again.";
      toast.error(message, { id: toastId });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <Toaster position="top-right" toastOptions={{ duration: 3500 }} />
      <Link className="auth-brand" href="/"><span className="wordmark-mark">K</span> kyro</Link>
      <section className="auth-card" aria-labelledby="register-heading">
        <p className="overline">GET STARTED</p>
        <h1 id="register-heading">Create your account</h1>
        <p className="auth-intro">A little space for your biggest ideas.</p>

        <form className="auth-form" onSubmit={(event) => { event.preventDefault(); void handleRegister(); }}>
          <label htmlFor="full-name">Full name</label>
          <input id="full-name" type="text" autoComplete="name" placeholder="Your name" value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} required />

          <label htmlFor="email">Email address</label>
          <input id="email" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />

          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="new-password" minLength={8} placeholder="At least 8 characters" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required />

          <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating account…" : "Create account"}</button>
        </form>
        <p className="auth-route-note">Already have an account? <Link href="/login">Sign in</Link></p>
      </section>
      <p className="auth-bottom">A soft place for serious work.</p>
    </main>
  );
}