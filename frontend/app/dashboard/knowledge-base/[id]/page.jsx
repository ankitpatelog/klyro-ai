"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  Bot,
  FileText,
  Trash2,
  Upload,
  Server,
  AlertCircle,
  Loader2,
} from "lucide-react";
import axios from "axios";

export default function KnowledgeBaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const kbId = Array.isArray(params?.id) ? params.id[0] : params?.id;

  const [knowledgeBase, setKnowledgeBase] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // API Base URL
  const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

  async function fetchKnowledgeBaseDetails() {
    setIsLoading(true);
    try {
      const response = await axios.get(`${apiUrl}/knowledge-bases/knowledgebase/${kbId}`, {
        withCredentials: true,
      });

      const kbData = response.data;
      setKnowledgeBase(kbData);
      setDocuments(kbData.documents_list || kbData.documents || []);
    } catch (error) {
      setKnowledgeBase(null);
      setDocuments([]);
      toast.error("Unable to load knowledge base details.");
    } finally {
      setIsLoading(false);
    }
  }

  // Fetch single knowledge base details and its documents
  useEffect(() => {
    if (kbId) {
      // The state update occurs after the request resolves.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void fetchKnowledgeBaseDetails();
    }
  }, [kbId, apiUrl]);

  // Handle single file upload
  async function handleFileUpload(e) {
    e.preventDefault();
    if (!selectedFile) {
      toast.error("Please select a file to upload.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    setIsUploading(true);
    const toastId = toast.loading("Uploading document...");

    try {
      const response = await axios.post(
        `${apiUrl}/knowledge-bases/knowledgebase/${kbId}/documents`,
        formData,
        {
          withCredentials: true,
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const newDoc = response.data?.document || response.data || {
        id: crypto.randomUUID(),
        name: selectedFile.name,
        created_at: new Date().toISOString(),
      };

      setDocuments((prev) => [newDoc, ...prev]);

      setKnowledgeBase((prev) => ({
        ...prev,
        documents: (prev?.documents || 0) + 1,
      }));

      setSelectedFile(null);
      toast.success("Document uploaded successfully!", { id: toastId });

      const fileInput = document.getElementById("file-upload-input");
      if (fileInput) fileInput.value = "";
    } catch (error) {
      toast.error("Failed to upload document.", { id: toastId });
    } finally {
      setIsUploading(false);
    }
  }

  // Delete Individual Document
  async function handleDeleteDocument(docId, docName) {
    if (!docId) {
      toast.error("Invalid document identifier.");
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${docName || "this document"}"?`)) return;

    const toastId = toast.loading("Deleting document...");
    try {
      await axios.delete(`${apiUrl}/knowledge-bases/knowledgebase/${kbId}/documents/${docId}`, {
        withCredentials: true,
      });

      setDocuments((prev) => prev.filter((doc) => (doc.id || doc._id) !== docId));
      setKnowledgeBase((prev) => ({
        ...prev,
        documents: Math.max(0, (prev?.documents || 1) - 1),
      }));

      toast.success("Document deleted.", { id: toastId });
    } catch (error) {
      toast.error("Failed to delete document.", { id: toastId });
    }
  }

  // Delete Entire Knowledge Base
  async function handleDeleteKnowledgeBase() {
    if (!window.confirm(`Are you sure you want to delete this entire knowledge base?`)) return;

    const toastId = toast.loading("Deleting knowledge base...");
    try {
      await axios.delete(`${apiUrl}/knowledge-bases/knowledgebase/${kbId}`, {
        withCredentials: true,
      });
      toast.success("Knowledge base deleted.", { id: toastId });
      router.push("/dashboard/knowledge-base");
    } catch (error) {
      toast.error("Failed to delete knowledge base.", { id: toastId });
    }
  }

  // Initialize Chatbot Handler
  function handleInitializeChatbot() {
    toast.success("Initializing chatbot with this knowledge base...");
    router.push(`/dashboard/knowledge-base/${kbId}/chat`);
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm text-[#6d7484]">
        <Loader2 className="mr-2 h-5 w-5 animate-spin text-[#8172d8]" />
        Loading space details...
      </div>
    );
  }

  if (!knowledgeBase) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center px-6">
        <AlertCircle size={40} className="mb-3 text-[#b3261e]" />
        <h2 className="text-xl font-medium text-[#273045]">Knowledge Base Not Found</h2>
        <p className="mt-1 text-sm text-[#6d7484]">
          The space you are looking for does not exist or has been removed.
        </p>
        <Link
          href="/dashboard/knowledge-base"
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[#8172d8] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#6658bb]"
        >
          <ArrowLeft size={16} /> Back to Hub
        </Link>
      </div>
    );
  }

  const isRunning = knowledgeBase.status === "running";

  return (
    <section className="min-w-0 pb-12">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">

        {/* Page header: navigation + actions */}
        <div className="mb-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <Link
            href="/dashboard/knowledge-base"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#6d7484] transition hover:text-[#8172d8] sm:text-base"
          >
            <ArrowLeft size={16} /> Back to Knowledge Bases
          </Link>

          <button
            onClick={handleDeleteKnowledgeBase}
            className="inline-flex items-center gap-2 rounded-xl border border-[#f5c6cb] bg-[#fff5f5] px-4 py-2.5 text-sm font-medium text-[#b3261e] transition hover:bg-[#fce8e6] sm:px-5"
          >
            <Trash2 size={15} /> Delete Base
          </button>
        </div>

        {/* Knowledge base header card */}
        <div className="mb-10 rounded-3xl border border-[#e8e5de] bg-white p-6 sm:p-10 shadow-sm">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_auto] lg:gap-10">
            <div className="flex flex-col gap-5">
              <div className="flex items-center gap-3">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#ece8ff] text-[#8172d8] sm:h-14 sm:w-14">
                  <BookOpen size={28} />
                </span>
                <div>
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      isRunning ? "bg-[#e6f4ea] text-[#137333]" : "bg-[#fce8e6] text-[#b3261e]"
                    } sm:py-1`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${isRunning ? "bg-[#34a853]" : "bg-[#ea4335]"}`} />
                    {isRunning ? "Running" : "Stopped"}
                  </span>
                </div>
              </div>

              <h1 className="text-3xl font-medium tracking-tight text-[#273045] sm:text-4xl">
                {knowledgeBase.name}
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#6d7484] sm:text-base">
                {knowledgeBase.description || "No description provided for this space."}
              </p>

              <button
                onClick={handleInitializeChatbot}
                disabled={documents.length === 0}
                className="mt-2 inline-flex items-center gap-2 rounded-xl bg-[#8172d8] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#6658bb] disabled:opacity-50 disabled:cursor-not-allowed sm:mt-0 sm:px-6 sm:py-3.5"
              >
                <Bot size={18} />
                Initialize Chatbot
              </button>
              {documents.length === 0 && (
                <p className="mt-2 text-xs text-[#a4a49b]">
                  Upload at least one document before initializing the chatbot.
                </p>
              )}
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-3 rounded-2xl border border-[#e8e5de] bg-[#fffdf8] p-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
                  <FileText size={16} />
                </span>
                <div>
                  <p className="text-xs text-[#6d7484]">Total Documents</p>
                  <p className="text-base font-semibold text-[#273045]">{documents.length}</p>
                </div>
              </div>

              <div className="flex items-center gap-3 rounded-2xl border border-[#e8e5de] bg-[#fffdf8] p-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
                  <Server size={16} />
                </span>
                <div>
                  <p className="text-xs text-[#6d7484]">Space Status</p>
                  <p className="text-base font-semibold text-[#273045] capitalize">
                    {knowledgeBase.status || "Running"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Body: upload + documents */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 lg:gap-10">

          {/* Single Document Upload */}
          <div className="rounded-3xl border border-[#e8e5de] bg-white p-6 sm:p-8 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-medium tracking-tight text-[#273045]">Upload Document</h2>
              <p className="mt-1 text-xs text-[#6d7484]">
                Add single documents one by one to enrich your knowledge base.
              </p>
            </div>

            <form onSubmit={handleFileUpload} className="space-y-4">
              <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[#d6cffa] bg-[#ece8ff]/10 p-8 sm:p-10 text-center transition hover:bg-[#ece8ff]/20 hover:border-[#c9c0f4]">
                <input
                  id="file-upload-input"
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                  className="hidden"
                />
                <label
                  htmlFor="file-upload-input"
                  className="flex cursor-pointer flex-col items-center justify-center"
                >
                  <span className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-[#ece8ff] text-[#8172d8]">
                    <Upload size={22} />
                  </span>
                  <p className="text-sm font-medium text-[#273045]">
                    {selectedFile ? selectedFile.name : "Click to browse or drag file here"}
                  </p>
                  <p className="mt-2 text-xs text-[#6d7484]">
                    Supports PDF, TXT, DOCX, MD, etc.
                  </p>
                </label>
              </div>

              {selectedFile && (
                <div className="flex items-center justify-between rounded-xl border border-[#e8e5de] bg-[#fffefa] px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#ece8ff] text-[#8172d8]">
                      <FileText size={14} />
                    </span>
                    <span className="text-xs font-medium text-[#273045] truncate max-w-xs sm:max-w-md">
                      Selected: {selectedFile.name}
                    </span>
                  </div>
                  <button
                    type="submit"
                    disabled={isUploading}
                    className="inline-flex items-center gap-2 rounded-lg bg-[#8172d8] px-4 py-2.5 text-xs font-medium text-white transition hover:bg-[#6658bb] disabled:opacity-50 disabled:cursor-not-allowed sm:px-5"
                  >
                    {isUploading ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Upload size={14} />
                    )}
                    Upload File
                  </button>
                </div>
              )}
            </form>
          </div>

          {/* Uploaded Documents List */}
          <div className="rounded-3xl border border-[#e8e5de] bg-white p-6 sm:p-8 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-medium tracking-tight text-[#273045]">Documents in this Space</h2>
              <p className="mt-1 text-xs text-[#6d7484]">
                Manage, review, or delete individual files indexed within this base.
              </p>
            </div>

            {documents.length === 0 ? (
              <div className="mt-6 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[#e8e5de] p-10 sm:p-14 text-center">
                <FileText size={36} className="mb-3 text-[#a4a49b]" />
                <p className="text-sm font-medium text-[#273045]">No documents uploaded yet</p>
                <p className="mt-1 text-xs text-[#6d7484]">
                  Upload your first file above to get started.
                </p>
              </div>
            ) : (
              <div className="mt-6 divide-y divide-[#f0eee9]">
                {documents.map((doc, idx) => {
                  const docId = doc.id || doc._id;
                  const docName = doc.name || doc.filename || "Unnamed Document";

                  return (
                    <div
                      key={docId || idx}
                      className="flex items-center justify-between gap-3 rounded-xl p-3 hover:bg-[#f4f2fc] transition"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
                          <FileText size={16} />
                        </span>
                        <div className="truncate">
                          <p className="text-sm font-medium text-[#273045] truncate">
                            {docName}
                          </p>
                          <p className="text-[11px] text-[#6d7484]">
                            Added{" "}
                            {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "Recently"}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => handleDeleteDocument(docId, docName)}
                          aria-label="Delete document"
                          className="rounded-lg p-2 text-[#6d7484] transition hover:bg-[#fce8e6] hover:text-[#b3261e]"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

      </div>
    </section>
  );
}
