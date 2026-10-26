"use client";

import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import toast, { Toaster } from "react-hot-toast";
import { apiUrl, getSafeNextPath, loginPath } from "../../lib/auth-routes";

export default function VerifyEmailPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    void axios.get(`${apiUrl}/auth/me`, { withCredentials: true })
      .then((response) => {
        if (response.data.email_verified_at) {
          router.replace(getSafeNextPath(new URLSearchParams(window.location.search).get("next")));
          return;
        }
        setEmail(response.data.email);
      })
      .catch(() => router.replace(loginPath(`/verify-email${window.location.search}`)));
  }, [router]);
  async function requestCode() { setSending(true); try { await axios.post(`${apiUrl}/auth/email-verification/request`, {}, { withCredentials: true }); toast.success("A four-digit code was sent to your email."); } catch (error) { toast.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? "Could not send a code." : "Could not send a code."); } finally { setSending(false); } }
  async function verify(event: React.FormEvent) { event.preventDefault(); if (code.length !== 4) return; setVerifying(true); try { await axios.post(`${apiUrl}/auth/email-verification/verify`, { code }, { withCredentials: true }); toast.success("Email verified. You can now upload documents."); router.replace(getSafeNextPath(new URLSearchParams(window.location.search).get("next"))); } catch (error) { toast.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? "Could not verify the code." : "Could not verify the code."); } finally { setVerifying(false); } }
  return <main className="flex min-h-screen items-center justify-center bg-[#fffefa] p-5 text-[#273045]"><Toaster position="top-right" /><section className="w-full max-w-md rounded-3xl border border-[#e8e5de] bg-white p-7 shadow-sm"><p className="text-[10px] font-semibold tracking-[0.2em] text-[#8172d8]">EMAIL VERIFICATION</p><h1 className="mt-2 text-3xl font-medium tracking-tight">Verify your email</h1><p className="mt-3 text-sm leading-6 text-[#6d7484]">We use a four-digit code to protect document uploads. {email && <>The code will be sent to <strong>{email}</strong>.</>}</p><button onClick={() => void requestCode()} disabled={sending} className="mt-6 w-full rounded-xl border border-[#d6cffa] px-4 py-3 text-sm font-medium text-[#6658bb] disabled:opacity-50">{sending ? "Sending code..." : "Send verification code"}</button><form onSubmit={verify} className="mt-5"><label className="text-sm font-medium">Four-digit code<input value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 4))} inputMode="numeric" autoComplete="one-time-code" placeholder="0000" className="mt-2 w-full rounded-xl border border-[#ddd8f2] px-4 py-3 text-center font-mono text-2xl tracking-[0.5em] outline-none focus:border-[#8172d8]" /></label><button disabled={verifying || code.length !== 4} className="mt-4 w-full rounded-xl bg-[#8172d8] px-4 py-3 text-sm font-medium text-white disabled:opacity-50">{verifying ? "Verifying..." : "Verify email"}</button></form><Link href="/dashboard/settings" className="mt-5 block text-center text-sm font-medium text-[#7161d7]">Back to settings</Link></section></main>;
}
