"use client";

import Link from "next/link";
import { useState } from "react";
import { Send, FileText } from "lucide-react";
import { sendChat } from "@/lib/api";
import { CardStatic } from "@/components/ui/Card";

const SUGGESTIONS = [
  "Why is the model failing?",
  "Should we retrain?",
  "Is the knowledge graph outdated?",
  "What changed in user behavior?",
  "Which intents drifted the most?",
  "Explain current production risk",
];

type Msg = { role: "user" | "assistant"; content: string };

export function Copilot({ mode }: { mode: "model" | "chatbot" }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const reportHref = mode === "model" ? "/model/report" : "/chatbot/report";

  const send = async (text: string) => {
    if (!text.trim()) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const res = await sendChat(text);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.response ?? "No response." },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "Agent unavailable. Ensure backend (8000) and agent (8001) are running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CardStatic className="flex min-h-[480px] flex-col">
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium">AI reliability copilot</h3>
        <Link
          href={reportHref}
          className="flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs text-muted hover:text-white"
        >
          <FileText className="h-3.5 w-3.5" />
          Drift report
        </Link>
      </header>

      <div className="mb-3 flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => send(s)}
            className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted transition hover:border-white/20 hover:text-white"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="min-h-[280px] flex-1 space-y-3 overflow-y-auto pr-1">
        {messages.length === 0 && (
          <p className="text-sm text-muted">
            {mode === "chatbot"
              ? "Ask about retrieval failures, KB staleness, or conversational drift."
              : "Ask about PSI, confidence collapse, or retraining decisions."}
          </p>
        )}
        {messages.map((m, i) => (
          <IncidentMessage key={i} role={m.role} content={m.content} />
        ))}
        {loading && (
          <p className="animate-pulse text-xs text-muted">Analyzing production signals…</p>
        )}
      </div>

      <form
        className="mt-3 flex gap-2 border-t border-border pt-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Operational question…"
          className="flex-1 rounded-lg border border-border bg-[#0f0f0f] px-3 py-2 text-sm outline-none focus:border-white/30"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg border border-border bg-white px-3 py-2 text-black hover:bg-white/90 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </CardStatic>
  );
}

function IncidentMessage({
  role,
  content,
}: {
  role: "user" | "assistant";
  content: string;
}) {
  if (role === "user") {
    return (
      <p className="rounded-lg border border-border bg-[#0f0f0f] px-3 py-2 text-sm">
        {content}
      </p>
    );
  }
  return (
    <article className="space-y-2 rounded-lg border border-border bg-card px-3 py-3 text-sm">
      <p className="text-[10px] uppercase tracking-wider text-muted">Incident assessment</p>
      <p className="whitespace-pre-wrap leading-relaxed text-white/90">{content}</p>
    </article>
  );
}
