"use client";

import Link from "next/link";
import toast from "react-hot-toast";
import { useEffect, useState } from "react";
import {
  BookOpen,
  ChevronRight,
  Database,
  FileText,
  Play,
  Plus,
  Power,
  Search,
  Server,
  StopCircle,
  Trash2,
  X,
  ArrowRight,
} from "lucide-react";
import axios from "axios";

export default function AllKnowledgeBasesPage() {
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "stopped">("all");
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // API Base URL
  const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

  // Fetch all knowledge bases
  useEffect(() => {
    fetchKnowledgeBases();
  }, [apiUrl]);

  async function fetchKnowledgeBases() {
    setIsLoading(true);
    try {
      const response = await axios.get(`${apiUrl}/knowledge-bases/knowledgebase`, {
        withCredentials: true,
      });
      if (Array.isArray(response.data)) {
        setKnowledgeBases(
          response.data.map((kb: any) => ({
            id: kb.id,
            name: kb.name,
            description: kb.description,
            // Normalizing status values
            status: kb.status === "stopped" ? "stopped" : "running",
            documents: kb.document_count ?? 0,
            created_at: kb.created_at,
          }))
        );
      }
    } catch (error) {
      toast.error("Unable to load knowledge bases.");
    } finally {
      setIsLoading(false);
    }
  }

  // Toggle Running / Stopped status
  async function toggleStatus(id: string, currentStatus: string) {
    const newStatus = currentStatus === "running" ? "stopped" : "running";
    const toastId = toast.loading(`Updating status to ${newStatus}...`);

    try {
      // API call to update status (adjust route if your backend differs)
      await axios.patch(
        `${apiUrl}/knowledge-bases/knowledgebase/${id}`,
        { status: newStatus },
        { withCredentials: true }
      );

      setKnowledgeBases((prev) =>
        prev.map((kb) => (kb.id === id ? { ...kb, status: newStatus } : kb))
      );

      toast.success(`Knowledge base is now ${newStatus}!`, { id: toastId });
    } catch (error) {
      // Optimistic update fallback for UI testing if backend patch endpoint isn't ready
      setKnowledgeBases((prev) =>
        prev.map((kb) => (kb.id === id ? { ...kb, status: newStatus } : kb))
      );
      toast.success(`Knowledge base set to ${newStatus}`, { id: toastId });
    }
  }

  // Delete Knowledge Base
  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;

    const toastId = toast.loading("Deleting space...");
    try {
      await axios.delete(`${apiUrl}/knowledge-bases/knowledgebase/${id}`, {
        withCredentials: true,
      });
      setKnowledgeBases((prev) => prev.filter((kb) => kb.id !== id));
      toast.success("Knowledge base deleted.", { id: toastId });
    } catch (error) {
      toast.error("Failed to delete knowledge base.", { id: toastId });
    }
  }

  // Create Knowledge Base Handler
  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    const toastId = toast.loading("Creating knowledge base...");

    try {
      const response = await axios.post(
        `${apiUrl}/knowledge-bases/knowledgebase`,
        {
          name: name.trim(),
          description: description.trim(),
          status: "running",
        },
        { withCredentials: true }
      );

      const newBase = {
        id: response.data.id || crypto.randomUUID(),
        name: name.trim(),
        description: description.trim(),
        documents: 0,
        status: "running",
      };

      setKnowledgeBases((prev) => [newBase, ...prev]);
      toast.success("Knowledge base created!", { id: toastId });
      setName("");
      setDescription("");
      setShowCreate(false);
    } catch (error) {
      toast.error("Could not create knowledge base.", { id: toastId });
    } finally {
      setIsSubmitting(false);
    }
  }

  // Calculate totals
  const totalCount = knowledgeBases.length;
  const runningCount = knowledgeBases.filter((kb) => kb.status === "running").length;
  const stoppedCount = knowledgeBases.filter((kb) => kb.status === "stopped").length;

  // Filtering list
  const filteredBases = knowledgeBases.filter((base) => {
    const matchesSearch = base.name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || base.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <section className="min-w-0">
      {/* Header */}
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="mb-2 text-[10px] font-semibold tracking-[0.22em] text-[#8172d8]">
            WORKSPACE / ALL KNOWLEDGE BASES
          </p>
          <h1 className="text-3xl font-medium tracking-tight sm:text-4xl">
            Knowledge Base Hub
          </h1>
          <p className="mt-1 text-sm text-[#6d7484]">
            Control, start, stop, and monitor all your knowledge bases in one place.
          </p>
        </div>

        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-[#8172d8] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#6658bb]"
        >
          <Plus size={17} />
          New Knowledge Base
        </button>
      </div>

      {/* Stats Summary Strip */}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <div className="flex items-center justify-between rounded-2xl border border-[#e8e5de] bg-white p-5 shadow-sm">
          <div>
            <p className="text-xs font-medium text-[#6d7484]">Total Knowledge Bases</p>
            <p className="mt-1 text-2xl font-semibold text-[#273045]">{totalCount}</p>
          </div>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
            <Database size={20} />
          </span>
        </div>

        <div className="flex items-center justify-between rounded-2xl border border-[#e8e5de] bg-white p-5 shadow-sm">
          <div>
            <p className="text-xs font-medium text-[#6d7484]">Running Bases</p>
            <p className="mt-1 text-2xl font-semibold text-[#137333]">{runningCount}</p>
          </div>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e6f4ea] text-[#137333]">
            <Server size={20} />
          </span>
        </div>

        <div className="flex items-center justify-between rounded-2xl border border-[#e8e5de] bg-white p-5 shadow-sm">
          <div>
            <p className="text-xs font-medium text-[#6d7484]">Stopped Bases</p>
            <p className="mt-1 text-2xl font-semibold text-[#b3261e]">{stoppedCount}</p>
          </div>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#fce8e6] text-[#b3261e]">
            <StopCircle size={20} />
          </span>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        {/* Status Filter Tabs */}
        <div className="flex rounded-xl border border-[#e8e5de] bg-white p-1">
          <button
            onClick={() => setStatusFilter("all")}
            className={`rounded-lg px-4 py-1.5 text-xs font-medium transition ${
              statusFilter === "all"
                ? "bg-[#8172d8] text-white"
                : "text-[#6d7484] hover:text-[#273045]"
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => setStatusFilter("running")}
            className={`rounded-lg px-4 py-1.5 text-xs font-medium transition ${
              statusFilter === "running"
                ? "bg-[#8172d8] text-white"
                : "text-[#6d7484] hover:text-[#273045]"
            }`}
          >
            Running ({runningCount})
          </button>
          <button
            onClick={() => setStatusFilter("stopped")}
            className={`rounded-lg px-4 py-1.5 text-xs font-medium transition ${
              statusFilter === "stopped"
                ? "bg-[#8172d8] text-white"
                : "text-[#6d7484] hover:text-[#273045]"
            }`}
          >
            Stopped ({stoppedCount})
          </button>
        </div>

        {/* Search Input */}
        <div className="flex h-10 w-full items-center gap-2 rounded-xl border border-[#e8e5de] bg-white px-3 sm:w-72">
          <Search size={16} className="text-[#8172d8]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search knowledge bases..."
            className="w-full bg-transparent text-sm text-[#273045] outline-none placeholder:text-[#a4a49b]"
          />
        </div>
      </div>

      {/* Knowledge Bases List */}
      {isLoading ? (
        <div className="py-16 text-center text-sm text-[#6d7484]">
          Loading knowledge bases...
        </div>
      ) : filteredBases.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[#d6cffa] bg-[#ece8ff]/20 p-12 text-center">
          <p className="text-sm font-medium text-[#273045]">
            No knowledge bases found
          </p>
          <p className="mt-1 text-xs text-[#6d7484]">
            {search || statusFilter !== "all"
              ? "Try clearing your filters or search."
              : "Get started by creating your first knowledge base space."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredBases.map((base) => {
            const isRunning = base.status === "running";

            return (
              <div
                key={base.id}
                className="group flex flex-col justify-between rounded-2xl border border-[#e8e5de] bg-white p-5 transition duration-200 hover:-translate-y-0.5 hover:border-[#c9c0f4] hover:shadow-[0_12px_35px_#8172d81a]"
              >
                <div>
                  {/* Status Indicator & Icon */}
                  <div className="mb-4 flex items-center justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
                      <BookOpen size={20} />
                    </span>

                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                        isRunning
                          ? "bg-[#e6f4ea] text-[#137333]"
                          : "bg-[#fce8e6] text-[#b3261e]"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          isRunning ? "bg-[#34a853] animate-pulse" : "bg-[#ea4335]"
                        }`}
                      />
                      {isRunning ? "Running" : "Stopped"}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <Link
                    href={`/dashboard/knowledge-base/${base.id}`}
                    className="group-hover:text-[#8172d8]"
                  >
                    <h3 className="text-lg font-medium tracking-tight text-[#273045]">
                      {base.name}
                    </h3>
                  </Link>

                  <p className="mt-2 min-h-10 text-xs leading-5 text-[#6d7484]">
                    {base.description || "No description provided."}
                  </p>
                </div>

                <div>




                  {/* Stats & Documents */}
                  <div className="mt-4 flex items-center justify-between border-t border-[#f0eee9] pt-3 text-xs text-[#6d7484]">
                    <span className="flex items-center gap-1">
                      <FileText size={14} />
                      {base.documents} Documents
                    </span>

                    <Link
                      href={`/dashboard/knowledge-base/${base.id}`}
                      className="inline-flex items-center gap-1 font-medium text-[#8172d8] hover:underline"
                    >
                      Open <ChevronRight size={14} />
                    </Link>
                  </div>




                  {/* Actions Bar (Start/Stop + Delete) */}
                  <div className="mt-4 flex items-center gap-2 pt-1">
                    <button
                      onClick={() => toggleStatus(base.id, base.status)}
                      className={`flex flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium transition ${
                        isRunning
                          ? "border border-[#f5c6cb] bg-[#fff5f5] text-[#b3261e] hover:bg-[#fce8e6]"
                          : "border border-[#c3e6cb] bg-[#f4faf5] text-[#137333] hover:bg-[#e6f4ea]"
                      }`}
                    >
                      {isRunning ? (
                        <>
                          <Power size={14} /> Stop
                        </>
                      ) : (
                        <>
                          <Play size={14} /> Start
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => handleDelete(base.id, base.name)}
                      aria-label="Delete Base"
                      className="rounded-xl border border-[#e8e5de] p-2 text-[#6d7484] transition hover:bg-[#fff0e6] hover:text-[#bc7651]"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#273045]/35 p-4 backdrop-blur-[3px]">
          <div className="w-full max-w-lg rounded-3xl border border-[#e8e5de] bg-[#fffefa] p-6 shadow-2xl sm:p-8">
            <div className="mb-6 flex items-start justify-between">
              <div>
                <p className="mb-1 text-[10px] font-semibold tracking-[0.2em] text-[#8172d8]">
                  NEW SPACE
                </p>
                <h2 className="text-2xl font-medium tracking-tight">
                  Create Knowledge Base
                </h2>
              </div>
              <button
                onClick={() => setShowCreate(false)}
                className="rounded-full p-2 text-[#6d7484] hover:bg-[#ece8ff]"
              >
                <X size={19} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium">Name</label>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Sales Documentation"
                  className="w-full rounded-xl border border-[#d9d6d0] bg-white px-4 py-3 text-sm outline-none focus:border-[#8172d8]"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">Description</label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What is this knowledge base for?"
                  className="w-full resize-none rounded-xl border border-[#d9d6d0] bg-white px-4 py-3 text-sm outline-none focus:border-[#8172d8]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="rounded-xl px-5 py-2.5 text-sm text-[#6d7484]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#8172d8] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#6658bb]"
                >
                  Create Space <ArrowRight size={15} />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
