"use client";
import { useState, useRef, useEffect } from "react";
import { streamQuery } from "@/lib/api";
import { FileText, Send, Zap, Brain, ChevronDown } from "lucide-react";
import Link from "next/link";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: { source: string; page: number | string; citation_id: string }[];
  streaming?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [useSmart, setUseSmart] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const bottomRef = useRef<HTMLDivElement>(null);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setLoading(true);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMsg },
      { role: "assistant", content: "", streaming: true },
    ]);

    stopRef.current = streamQuery(
      { query: userMsg, session_id: sessionId, use_smart_model: useSmart },
      (text) => {
        setMessages((prev) => {
          const updated = [...prev];
          const idx = updated.length - 1;
          if (updated[idx].role === "assistant")
            updated[idx] = { ...updated[idx], content: updated[idx].content + text };
          return updated;
        });
      },
      (sources) => {
        setMessages((prev) => {
          const updated = [...prev];
          const idx = updated.length - 1;
          if (updated[idx].role === "assistant")
            updated[idx] = { ...updated[idx], sources };
          return updated;
        });
      },
      () => {
        setMessages((prev) => {
          const updated = [...prev];
          const idx = updated.length - 1;
          if (updated[idx].role === "assistant")
            updated[idx] = { ...updated[idx], streaming: false };
          return updated;
        });
        setLoading(false);
      },
      (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            last.content = `Error: ${err}`;
            last.streaming = false;
          }
          return updated;
        });
        setLoading(false);
      }
    );
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-white">LegalRAG</span>
          <span className="text-xs text-gray-500 hidden sm:block">AWS Bedrock · OpenSearch</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setUseSmart((v) => !v)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition ${
              useSmart
                ? "border-purple-500 text-purple-400 bg-purple-500/10"
                : "border-gray-700 text-gray-400"
            }`}
          >
            {useSmart ? <Brain className="w-3 h-3" /> : <Zap className="w-3 h-3" />}
            {useSmart ? "Sonnet 4.6" : "Haiku 4.5"}
          </button>
          <Link
            href="/upload"
            className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
          >
            Upload Docs
          </Link>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 max-w-3xl mx-auto w-full">
        {messages.length === 0 && (
          <div className="text-center pt-20 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium text-gray-400">Ask about your legal documents</p>
            <p className="text-sm mt-1">Upload documents first, then ask questions here.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm"
                  : "bg-gray-800 text-gray-100 rounded-bl-sm"
              }`}
            >
              {msg.content || (msg.streaming && <span className="animate-pulse">▋</span>)}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <p className="text-xs text-gray-400 mb-1">Sources:</p>
                  <div className="space-y-1">
                    {msg.sources.map((s, si) => (
                      <div key={si} className="text-xs text-blue-400 font-mono">
                        [{si + 1}] {s.source} — Page {s.page}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-4 max-w-3xl mx-auto w-full">
        <div className="flex gap-2 bg-gray-800 rounded-2xl p-2 border border-gray-700">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Ask about contracts, policies, regulations..."
            className="flex-1 bg-transparent resize-none text-sm text-gray-100 placeholder-gray-500 outline-none px-2 py-1 max-h-32"
            rows={1}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="w-9 h-9 flex items-center justify-center bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl transition flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-xs text-gray-600 mt-2">
          Answers are grounded in your documents only. Always verify with a legal professional.
        </p>
      </div>
    </div>
  );
}
