"use client";

import { useDriftView } from "@/hooks/useDriftView";
import { useChatbotMetrics } from "@/hooks/useDriftView";
import { CardStatic } from "@/components/ui/Card";
import { KB_TOPICS_DEFAULT } from "@/lib/glossary";
import { EmptyState } from "./EmptyState";

const DEMO_CONVERSATIONS = [
  {
    query: "How do I use the v2 API webhook?",
    response: "Please contact support for API documentation.",
    status: "fallback",
  },
  {
    query: "Your pricing page shows old tiers",
    response: "I'm not sure about current pricing.",
    status: "stale KB",
  },
  {
    query: "Can I get a refund after 60 days?",
    response: "I don't have information about refund windows.",
    status: "negative",
  },
];

export function ChatbotDriftPanel() {
  const v = useDriftView();
  const { metrics, kb } = useChatbotMetrics();
  const conv = (v.report.conversational_drift ?? {}) as Record<string, unknown>;
  const stale = (kb.stale_topics ?? []) as string[];
  const topicAges = (kb.knowledge_topic_ages_days ?? {}) as Record<string, number>;

  if (!v.hasData) return <EmptyState systemType="chatbot" />;

  const rows = KB_TOPICS_DEFAULT.map(({ topic, key, days }) => {
    const age = topicAges[key] ?? days;
    const isStale = stale.includes(key) || age >= 60;
    return { topic, updated: `${age}d ago`, status: isStale ? "stale" : "healthy" };
  });

  return (
    <div className="space-y-6">
      <CardStatic>
        <h3 className="mb-4 text-sm font-medium">Conversational drift</h3>
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          <li className="rounded-lg border border-border bg-[#0f0f0f] px-3 py-2">
            Greeting shift: {String(conv.greeting_frequency_shift ?? "—")}
          </li>
          <li className="rounded-lg border border-border bg-[#0f0f0f] px-3 py-2">
            FAQ pattern shift: {String(conv.faq_pattern_shift ?? "—")}
          </li>
          <li className="rounded-lg border border-border bg-[#0f0f0f] px-3 py-2">
            Vocabulary drift: {String(conv.vocabulary_drift_score ?? "—")}
          </li>
          <li className="rounded-lg border border-border bg-[#0f0f0f] px-3 py-2">
            Avg confidence: {metrics.avg_confidence ?? "—"}
          </li>
        </ul>
      </CardStatic>

      <CardStatic>
        <h3 className="mb-4 text-sm font-medium">Knowledge base health</h3>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wider text-muted">
              <th className="pb-2">Topic</th>
              <th className="pb-2">Last updated</th>
              <th className="pb-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.topic} className="border-b border-border/40">
                <td className="py-2">{r.topic}</td>
                <td className="py-2 text-muted">{r.updated}</td>
                <td className={`py-2 ${r.status === "stale" ? "text-warning" : "text-success"}`}>
                  {r.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardStatic>

      <CardStatic>
        <h3 className="mb-4 text-sm font-medium">Chat response monitor</h3>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-muted">
              <th className="pb-2">User query</th>
              <th className="pb-2">Bot response</th>
              <th className="pb-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_CONVERSATIONS.map((c) => (
              <tr key={c.query} className="border-t border-border/40">
                <td className="py-2 pr-2 align-top">{c.query}</td>
                <td className="py-2 pr-2 align-top text-muted">{c.response}</td>
                <td className="py-2 align-top text-alert">{c.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardStatic>

      <CardStatic>
        <h3 className="mb-3 text-sm font-medium">Retrieval failure analysis</h3>
        <p className="text-sm leading-relaxed text-white/90">
          {String(
            v.diagnosis.root_cause ??
              v.diagnosis.diagnosis ??
              "Failures may originate from stale API documentation rather than statistical drift."
          )}
        </p>
      </CardStatic>
    </div>
  );
}
