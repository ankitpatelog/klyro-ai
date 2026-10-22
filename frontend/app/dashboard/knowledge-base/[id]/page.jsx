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

  // Fetch single knowledge base details and its documents
  useEffect(() => {
    if (kbId) {
      fetchKnowledgeBaseDetails();
    }
  }, [kbId, apiUrl]);

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
    router.push(`/dashboard/chat?kb=${kbId}`);
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
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <AlertCircle size={40} className="mb-3 text-[#b3261e]" />
        <h2 className="text-xl font-medium text-[#273045]">Knowledge Base Not Found</h2>
        <p className="mt-1 text-sm text-[#6d7484]">The space you are looking for does not exist or has been removed.</p>
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
      {/* Back Button & Breadcrumbs */}
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/dashboard/knowledge-base"
          className="inline-flex items-center gap-2 text-xs font-medium text-[#6d7484] transition hover:text-[#273045]"
        >
          <ArrowLeft size={15} /> Back to Knowledge Bases
        </Link>

        <button
          onClick={handleDeleteKnowledgeBase}
          className="inline-flex items-center gap-1.5 rounded-xl border border-[#f5c6cb] bg-[#fff5f5] px-3.5 py-2 text-xs font-medium text-[#b3261e] transition hover:bg-[#fce8e6]"
        >
          <Trash2 size={14} /> Delete Base
        </button>
      </div>

      {/* Header Info Card */}
      <div className="mb-8 rounded-3xl border border-[#e8e5de] bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#ece8ff] text-[#8172d8]">
                <BookOpen size={24} />
              </span>
              <div>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    isRunning ? "bg-[#e6f4ea] text-[#137333]" : "bg-[#fce8e6] text-[#b3261e]"
                  }`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${isRunning ? "bg-[#34a853]" : "bg-[#ea4335]"}`} />
                  {isRunning ? "Running" : "Stopped"}
                </span>
              </div>
            </div>

            <h1 className="text-2xl font-medium tracking-tight text-[#273045] sm:text-3xl">
              {knowledgeBase.name}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#6d7484]">
              {knowledgeBase.description || "No description provided for this space."}
            </p>
          </div>

          <button
            onClick={handleInitializeChatbot}
            className="inline-flex items-center gap-2 rounded-xl bg-[#8172d8] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#6658bb] shadow-sm"
          >
            <Bot size={18} />
            Initialize Chatbot
          </button>
        </div>

        {/* Quick Stats Grid */}
        <div className="mt-6 grid gap-4 border-t border-[#f0eee9] pt-6 sm:grid-cols-2">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
              <FileText size={16} />
            </span>
            <div>
              <p className="text-xs text-[#6d7484]">Total Documents</p>
              <p className="text-base font-semibold text-[#273045]">{documents.length}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
              <Server size={16} />
            </span>
            <div>
              <p className="text-xs text-[#6d7484]">Space Status</p>
              <p className="text-base font-semibold text-[#273045] capitalize">{knowledgeBase.status || "Running"}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Single Document Upload Section */}
      <div className="mb-8 rounded-3xl border border-[#e8e5de] bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-medium tracking-tight text-[#273045]">Upload Document</h2>
        <p className="mt-1 text-xs text-[#6d7484]">Add single documents one by one to enrich your knowledge base.</p>

        <form onSubmit={handleFileUpload} className="mt-5 space-y-4">
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[#d6cffa] bg-[#ece8ff]/10 p-6 text-center transition hover:bg-[#ece8ff]/20">
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
              <span className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-[#ece8ff] text-[#8172d8]">
                <Upload size={20} />
              </span>
              <p className="text-sm font-medium text-[#273045]">
                {selectedFile ? selectedFile.name : "Click to browse or drag file here"}
              </p>
              <p className="mt-1 text-xs text-[#6d7484]">Supports PDF, TXT, DOCX, MD, etc.</p>
            </label>
          </div>

          {selectedFile && (
            <div className="flex items-center justify-between rounded-xl border border-[#e8e5de] bg-[#fffefa] px-4 py-3">
              <span className="text-xs font-medium text-[#273045] truncate max-w-xs sm:max-w-md">
                Selected: {selectedFile.name}
              </span>
              <button
                type="submit"
                disabled={isUploading}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#8172d8] px-4 py-2 text-xs font-medium text-white transition hover:bg-[#6658bb]"
              >
                {isUploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                Upload File
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Uploaded Documents List */}
      <div className="rounded-3xl border border-[#e8e5de] bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-medium tracking-tight text-[#273045]">Documents in this Space</h2>
        <p className="mt-1 text-xs text-[#6d7484]">Manage, review, or delete individual files indexed within this base.</p>

        {documents.length === 0 ? (
          <div className="mt-6 flex flex-col items-center justify-center rounded-2xl border border-dashed border-[#e8e5de] p-8 text-center">
            <FileText size={32} className="mb-2 text-[#a4a49b]" />
            <p className="text-sm font-medium text-[#273045]">No documents uploaded yet</p>
            <p className="mt-1 text-xs text-[#6d7484]">Upload your first file above to get started.</p>
          </div>
        ) : (
          <div className="mt-6 divide-y divide-[#f0eee9]">
            {documents.map((doc, idx) => {
              const docId = doc.id || doc._id;
              const docName = doc.name || doc.filename || "Unnamed Document";
              
              return (
                <div key={docId || idx} className="flex items-center justify-between py-3.5 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3 truncate">
                    <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]">
                      <FileText size={16} />
                    </span>
                    <div className="truncate">
                      <p className="text-sm font-medium text-[#273045] truncate">{docName}</p>
                      <p className="text-[11px] text-[#6d7484]">
                        Added {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "Recently"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDeleteDocument(docId, docName)}
                      aria-label="Delete document"
                      className="rounded-lg border border-[#e8e5de] p-2 text-[#6d7484] transition hover:bg-[#fff0e6] hover:text-[#bc7651]"
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
    </section>
  );
}
