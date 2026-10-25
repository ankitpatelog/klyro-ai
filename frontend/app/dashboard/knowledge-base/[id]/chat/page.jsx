"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import { ArrowLeft, Bot, FileText, Loader2, Send, Sparkles, UserRound } from "lucide-react";

function formatInline(text) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__)/g).map((part, index) => {
    if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) {
      return <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index} className="rounded bg-[#f4f2fc] px-1 py-0.5 font-mono text-[0.85em]">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function FormattedAnswer({ content }) {
  return (
    <div className="space-y-2.5">
      {content.split("\n").map((line, index) => {
        const heading = line.match(/^(#{1,3})\s+(.+)$/);
        const bullet = line.match(/^[-*]\s+(.+)$/);
        const numbered = line.match(/^(\d+)\.\s+(.+)$/);

        if (!line.trim()) return <div key={index} className="h-1" />;
        if (heading) {
          return <h3 key={index} className="pt-1 text-base font-semibold text-[#273045]">{formatInline(heading[2])}</h3>;
        }
        if (bullet) {
          return <div key={index} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#8172d8]" /><span>{formatInline(bullet[1])}</span></div>;
        }
        if (numbered) {
          return <div key={index} className="flex gap-2"><span className="font-semibold text-[#8172d8]">{numbered[1]}.</span><span>{formatInline(numbered[2])}</span></div>;
        }
        return <p key={index}>{formatInline(line)}</p>;
      })}
    </div>
  );
}

export default function KnowledgeBaseChatPage() {
  const params = useParams();
  const knowledgeBaseId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const [knowledgeBase, setKnowledgeBase] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const chatScrollRef = useRef(null);

  useEffect(() => {
    const chat = chatScrollRef.current;
    if (!chat) return;
    chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  async function loadChat() {
    setIsLoading(true);
    try {
      const kbResponse = await axios.get(`${apiUrl}/knowledge-bases/knowledgebase/${knowledgeBaseId}`, {
        withCredentials: true,
      });
      setKnowledgeBase(kbResponse.data);
      const historyResponse = await axios.get(`${apiUrl}/rag/knowledge-bases/${knowledgeBaseId}/conversation`, {
        withCredentials: true,
      });
      setMessages(historyResponse.data || []);
    } catch (error) {
      if (error.response?.status === 409) {
        toast.error("Upload and finish embedding at least 2 documents before chatting.");
      } else {
        toast.error("Unable to load this knowledge base chat.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!knowledgeBaseId) return;
    // The state update occurs after the request resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadChat();
  }, [knowledgeBaseId, apiUrl]);

  async function sendQuestion(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || isSending) return;

    const optimisticMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, optimisticMessage]);
    setQuestion("");
    setIsSending(true);

    try {
      const response = await axios.post(
        `${apiUrl}/rag/questions`,
        { knowledge_base_id: knowledgeBaseId, question: text, stream: false },
        { withCredentials: true }
      );
      setMessages((current) => [
        ...current,
        {
          id: response.data.request_id,
          role: "assistant",
          content: response.data.answer,
          citations: response.data.citations || [],
          created_at: response.data.created_at,
        },
      ]);
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== optimisticMessage.id));
      toast.error(error.response?.data?.detail || "The assistant could not answer right now.");
    } finally {
      setIsSending(false);
    }
  }

  function formatTime(isoString) {
    if (!isoString) return "";
    return new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm text-[#6d7484]">
        <Loader2 className="mr-2 h-5 w-5 animate-spin text-[#8172d8]" /> Loading knowledge base chat...
      </div>
    );
  }

  const completedDocuments = (knowledgeBase?.documents || []).filter((document) => document.status === "completed").length;
  const isReady = completedDocuments >= 2;

  return (
    <section className="mx-auto flex h-[calc(100dvh-9rem)] min-h-[36rem] max-w-5xl flex-col pb-8">
      <div className="mb-5 flex shrink-0 items-center justify-between gap-4">
        <Link href={`/dashboard/knowledge-base/${knowledgeBaseId}`} className="inline-flex items-center gap-2 text-xs font-medium text-[#6d7484] hover:text-[#273045]">
          <ArrowLeft size={15} /> Back to {knowledgeBase?.name || "Knowledge Base"}
        </Link>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${isReady ? "bg-[#e6f4ea] text-[#137333]" : "bg-[#fff0e6] text-[#bc7651]"}`}>
          {isReady ? `${completedDocuments} documents ready` : `${completedDocuments}/2 documents ready`}
        </span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-3xl border border-[#e8e5de] bg-white shadow-sm">
        <div className="flex shrink-0 items-center gap-3 border-b border-[#f0eee9] p-5">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ece8ff] text-[#8172d8]"><Bot size={20} /></span>
          <div>
            <h1 className="font-medium text-[#273045]">{knowledgeBase?.name || "Knowledge Base"} Assistant</h1>
            <p className="text-xs text-[#6d7484]">Answers are grounded only in this knowledge base’s completed documents.</p>
          </div>
        </div>

        <div ref={chatScrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5 sm:p-7">
          {!isReady ? (
            <div className="mx-auto mt-12 max-w-md rounded-2xl border border-dashed border-[#d6cffa] bg-white p-7 text-center">
              <FileText className="mx-auto mb-3 text-[#8172d8]" size={30} />
              <h2 className="font-medium text-[#273045]">Chat will be ready soon</h2>
              <p className="mt-2 text-sm leading-6 text-[#6d7484]">Upload and finish embedding at least two documents in this knowledge base before asking questions.</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="mx-auto mt-12 max-w-md text-center">
              <Sparkles className="mx-auto mb-3 text-[#8172d8]" size={30} />
              <h2 className="font-medium text-[#273045]">Start this knowledge base chat</h2>
              <p className="mt-2 text-sm leading-6 text-[#6d7484]">Ask a question about the completed documents in {knowledgeBase?.name}.</p>
            </div>
          ) : (
            <div className="space-y-5">
              {messages.map((message) => (
                <div key={message.id} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  {message.role === "assistant" && (
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#ece8ff] text-[#8172d8]">
                      <Bot size={15} />
                    </span>
                  )}
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${message.role === "user" ? "bg-[#8172d8] text-white" : "border border-[#e8e5de] bg-white text-[#273045]"}`}>
                    {message.role === "assistant" ? (
                      <FormattedAnswer content={message.content} />
                    ) : (
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    )}
                    <div className="flex items-center gap-1 text-[10px] text-[#6d7484] mt-2">
                      {formatTime(message.created_at)}
                    </div>
                    {message.role === "assistant" && message.citations?.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        <span className="text-[10px] font-medium text-[#6d7484]">Sources:</span>
                        {message.citations.map((citation, idx) => (
                          <span key={idx} className="rounded-full border border-[#d9d6d0] bg-[#fffefa] px-2 py-0.5 text-[10px] text-[#6d7484] truncate max-w-xs" title={citation.source_file_name}>
                            {citation.source_file_name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  {message.role === "user" && (
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#e8e5de] text-[#6d7484]">
                      <UserRound size={15} />
                    </span>
                  )}
                </div>
              ))}
              {isSending && (
                <div className="flex items-center gap-2 text-sm text-[#6d7484]">
                  <Loader2 size={15} className="animate-spin text-[#8172d8]" /> Finding an answer...
                </div>
              )}
            </div>
          )}
        </div>

        <form onSubmit={sendQuestion} className="border-t border-[#f0eee9] bg-white p-4 sm:p-5">
          <div className="flex items-end gap-3 rounded-2xl border border-[#d9d6d0] bg-[#fffefa] p-2 focus-within:border-[#8172d8]">
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} disabled={!isReady || isSending} rows={2} placeholder={isReady ? "Ask about this knowledge base..." : "Complete two document embeddings to enable chat"} className="min-h-12 flex-1 resize-none bg-transparent px-2 py-1 text-sm text-[#273045] outline-none placeholder:text-[#a4a49b] disabled:cursor-not-allowed" />
            <button type="submit" disabled={!isReady || isSending || !question.trim()} className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[#8172d8] text-white transition hover:bg-[#6658bb] disabled:cursor-not-allowed disabled:opacity-40" aria-label="Send question">
              {isSending ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
