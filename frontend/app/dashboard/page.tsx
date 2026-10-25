"use client";

import Link from "next/link";
import toast from "react-hot-toast";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  ChevronRight,
  Files,
  Plus,
  Search,
  Sparkles,
  UploadCloud,
  X,
  Loader2,
} from "lucide-react";
import axios from "axios";

type KnowledgeBase = {
  id: string;
  user_id?: string;
  name: string;
  description?: string;
  status: string;
  document_count?: number;
  documents: number;
  created_at?: string;
};

export default function DashboardPage() {
  // State for storing list of knowledge bases
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Search input state
  const [search, setSearch] = useState("");
  
  // Modal visibility state
  const [showCreate, setShowCreate] = useState(false);
  
  // Form input states
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // API Base URL (removes trailing slash if present)
  const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

  // Fetch all knowledge bases when the page loads
  useEffect(() => {
    async function fetchKnowledgeBases() {
      try {
        const response = await axios.get(`${apiUrl}/knowledge-bases/knowledgebase`, {
          withCredentials: true,
        });

        const data = response.data;

        if (Array.isArray(data)) {
          setKnowledgeBases(
            data.map((kb: Omit<KnowledgeBase, "documents">) => ({
              id: kb.id,
              user_id: kb.user_id || kb.id,
              name: kb.name,
              description: kb.description,
              status: kb.status || "ready",
              documents: kb.document_count ?? 0,
              created_at: kb.created_at,
            }))
          );
        }
      } catch (error) {
        toast.error("Unable to load knowledge bases. Please try again.");
      } finally {
        setIsLoading(false);
      }
    }
    fetchKnowledgeBases();
  }, [apiUrl]);

  // Handle creating a new knowledge base
  async function handleCreateKnowledgeBase(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!name.trim()) return;

    setIsSubmitting(true);
    const toastId = toast.loading("Creating your knowledge base...");

    try {
      const response = await axios.post(`${apiUrl}/knowledge-bases/knowledgebase`, {
        name: name.trim(),
        description: description.trim(),
        status: "active",
        document_limit: 10,
      }, {
        withCredentials: true,
      });

      // New item returned from backend or created locally
      const newBase = {
        id: response.data.id || crypto.randomUUID(),
        name: name.trim(),
        description: description.trim(),
        documents: 0,
        status: "ready",
      };

      // Update state instantly so the UI reflects the new item
      setKnowledgeBases((previous) => [newBase, ...previous]);

      toast.success("Knowledge base created!", { id: toastId });
      
      // Reset form & close modal
      setName("");
      setDescription("");
      setShowCreate(false);
    } catch (error) {
      const message = axios.isAxiosError<{ detail?: string }>(error)
        ? error.response?.data.detail ?? "We couldn’t create your knowledge base. Please try again."
        : "Unable to reach the server. Please try again.";
      toast.error(message, { id: toastId });
    } finally {
      setIsSubmitting(false);
    }
  }

  // Filter knowledge bases based on search input
  const filteredBases = knowledgeBases.filter((base) =>
    base.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <section className="min-w-0">
        <div className="mb-12">
          <p className="mb-4 text-[10px] font-semibold tracking-[0.22em] text-[#8172d8]">
            YOUR WORKSPACE / OVERVIEW
          </p>

          <h1 className="max-w-2xl text-4xl font-medium leading-[1.13] tracking-[-0.055em] sm:text-5xl">
            A little space for{" "}
            <span className="font-serif italic text-[#8172d8]">
              knowledge.
            </span>
          </h1>

          <p className="mt-5 max-w-xl text-sm leading-7 text-[#6d7484] sm:text-base">
            Bring your documents together. Give your ideas somewhere to
            grow. Everything you need, without the noise.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-4">
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-[#8172d8] px-5 py-3.5 text-sm font-medium text-white transition hover:-translate-y-0.5 hover:bg-[#6658bb]"
            >
              <Plus size={17} />
              Create knowledge base
              <ArrowRight size={16} />
            </button>

            <Link
              href="/dashboard/knowledge-base"
              className="text-sm text-[#6d7484] transition hover:text-[#8172d8]"
            >
              Browse knowledge bases
            </Link>
          </div>
        </div>

        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-medium tracking-tight">
              Your knowledge bases
            </h2>
            <p className="mt-1 text-sm text-[#6d7484]">
              A home for everything your AI needs to know.
            </p>
          </div>

          <div className="flex h-10 w-full items-center gap-2 rounded-xl border border-[#e8e5de] bg-white px-3 sm:w-64">
            <Search size={16} className="text-[#8172d8]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Find a knowledge base..."
              className="w-full bg-transparent text-sm text-[#273045] outline-none placeholder:text-[#a4a49b]"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex min-h-56 items-center justify-center rounded-2xl border border-dashed border-[#d6cffa] bg-white text-sm text-[#6d7484]">
            <Loader2 size={18} className="mr-2 animate-spin text-[#8172d8]" /> Loading knowledge bases...
          </div>
        ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {filteredBases.map((base, index) => (
            <Link
              key={base.id}
              href={`/dashboard/knowledge-base/${base.id}`}
              className="group rounded-2xl border border-[#e8e5de] bg-white p-5 transition duration-200 hover:-translate-y-0.5 hover:border-[#c9c0f4] hover:shadow-[0_12px_35px_#8172d81a]"
            >
              <div className="mb-6 flex items-start justify-between">
                <span
                  className={`flex h-11 w-11 items-center justify-center rounded-xl ${
                    index % 2 === 0
                      ? "bg-[#ece8ff] text-[#8172d8]"
                      : "bg-[#fff0e6] text-[#bc7651]"
                  }`}
                >
                  {index % 2 === 0 ? (
                    <BookOpen size={21} />
                  ) : (
                    <Files size={21} />
                  )}
                </span>

                <ChevronRight
                  size={18}
                  className="text-[#b6b4bf] transition group-hover:translate-x-1 group-hover:text-[#8172d8]"
                />
              </div>

              <h3 className="text-lg font-medium tracking-tight">
                {base.name}
              </h3>

              <p className="mt-2 min-h-10 text-sm leading-5 text-[#6d7484]">
                {base.description || "Your knowledge, organized."}
              </p>

              <div className="mt-6 flex items-center justify-between border-t border-[#f0eee9] pt-4">
                <span className="text-xs text-[#6d7484]">
                  {base.documents} documents
                </span>

                <span className="flex items-center gap-1.5 text-xs text-[#52825b]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#7ab89c]" />
                  {base.status === "ready" || base.status === "active" ? "Ready" : "Processing"}
                </span>
              </div>
            </Link>
          ))}

          <button
            onClick={() => setShowCreate(true)}
            className="flex min-h-[235px] flex-col items-center justify-center rounded-2xl border border-dashed border-[#d6cffa] bg-[#ece8ff]/30 p-6 text-center transition hover:border-[#8172d8] hover:bg-[#ece8ff]/60"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#ece8ff] text-[#8172d8]">
              <Plus size={21} />
            </span>
            <span className="mt-4 text-sm font-medium">
              Create a new space
            </span>
            <span className="mt-2 text-xs text-[#6d7484]">
              Start with a fresh collection of knowledge.
            </span>
          </button>
        </div>
        )}

        {filteredBases.length === 0 && search.trim() && (
          <p className="mt-6 text-sm text-[#6d7484]">
            No knowledge bases match &quot;{search}&quot;.
          </p>
        )}

        <div className="mt-10 overflow-hidden rounded-2xl bg-[#ece8ff]">
          <div className="grid items-center gap-6 p-6 sm:grid-cols-[1fr_auto] sm:p-8">
            <div>
              <span className="mb-4 inline-flex items-center gap-2 text-xs font-medium text-[#6658bb]">
                <Sparkles size={15} />
                A BETTER WAY TO FIND ANSWERS
              </span>

              <h2 className="max-w-md text-2xl font-medium tracking-tight">
                Start with what you know.
              </h2>

              <p className="mt-3 max-w-md text-sm leading-6 text-[#6d7484]">
                Add your PDFs, documents and notes. Kyro organizes your
                knowledge so you can find answers through conversation.
              </p>

              <button
                onClick={() => setShowCreate(true)}
                className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-[#6658bb] transition hover:text-[#4d409a]"
              >
                Create your knowledge base
                <ArrowRight size={16} />
              </button>
            </div>

            <div className="hidden h-28 w-28 items-center justify-center rounded-3xl border border-white/80 bg-white/50 sm:flex">
              <UploadCloud
                size={42}
                strokeWidth={1.2}
                className="text-[#8172d8]"
              />
            </div>
          </div>
        </div>

        <footer className="mt-10 flex flex-wrap justify-between gap-3 border-t border-[#e8e5de] pt-5 text-xs text-[#92939e]">
          <span>A quieter workspace for better answers.</span>
          <span>Kyro AI · Your knowledge, your way.</span>
        </footer>
      </section>

      {/* Create Knowledge Base Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#273045]/35 p-4 backdrop-blur-[3px]">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-title"
            className="w-full max-w-lg rounded-3xl border border-[#e8e5de] bg-[#fffefa] p-6 shadow-[0_20px_60px_#44356c24] sm:p-8"
          >
            <div className="mb-7 flex items-start justify-between">
              <div>
                <p className="mb-2 text-[10px] font-semibold tracking-[0.2em] text-[#8172d8]">
                  A NEW BEGINNING
                </p>
                <h2
                  id="create-title"
                  className="text-2xl font-medium tracking-tight"
                >
                  Create a knowledge base
                </h2>
                <p className="mt-2 text-sm leading-6 text-[#6d7484]">
                  Give your knowledge a name. You can add documents next.
                </p>
              </div>

              <button
                onClick={() => setShowCreate(false)}
                aria-label="Close dialog"
                className="rounded-full p-2 text-[#6d7484] transition hover:bg-[#ece8ff] hover:text-[#8172d8]"
              >
                <X size={19} />
              </button>
            </div>

            <form onSubmit={handleCreateKnowledgeBase} className="space-y-5">
              <div>
                <label
                  htmlFor="base-name"
                  className="mb-2 block text-sm font-medium"
                >
                  Knowledge base name
                </label>
                <input
                  id="base-name"
                  required
                  maxLength={120}
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. HR Policies"
                  className="w-full rounded-xl border border-[#d9d6d0] bg-white px-4 py-3 text-sm outline-none transition placeholder:text-[#a4a49b] focus:border-[#8172d8] focus:ring-4 focus:ring-[#8172d8]/15"
                />
              </div>

              <div>
                <label
                  htmlFor="base-description"
                  className="mb-2 block text-sm font-medium"
                >
                  Description
                  <span className="ml-2 font-normal text-[#6d7484]">
                    Optional
                  </span>
                </label>
                <textarea
                  id="base-description"
                  rows={3}
                  maxLength={2000}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What kind of knowledge will live here?"
                  className="w-full resize-none rounded-xl border border-[#d9d6d0] bg-white px-4 py-3 text-sm outline-none transition placeholder:text-[#a4a49b] focus:border-[#8172d8] focus:ring-4 focus:ring-[#8172d8]/15"
                />
              </div>

              <div className="flex flex-col-reverse gap-3 border-t border-[#e8e5de] pt-5 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="rounded-xl px-5 py-3 text-sm text-[#6d7484] transition hover:bg-[#ece8ff]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#8172d8] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#6658bb] disabled:opacity-50"
                >
                  {isSubmitting ? "Creating..." : "Create knowledge base"}
                  <ArrowRight size={16} />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
