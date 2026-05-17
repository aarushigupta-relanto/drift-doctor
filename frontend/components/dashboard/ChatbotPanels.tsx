"use client";

import { useDriftStore } from "@/lib/store";
import { CardStatic } from "@/components/ui/Card";
import { KB_TOPICS_DEFAULT } from "@/lib/glossary";

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

export function ChatbotPanels() {
  const latest = useDriftStore((s) => s.latest);
  const report = (latest?.report ?? {}) as Record<string, unknown>;
  const diagnosis = (latest?.diagnosis ?? {}) as Record<string, unknown>;
  const metrics = (report.chatbot_metrics ?? {}) as Record<string, number>;
  const conv = (report.conversational_drift ?? {}) as Record<string, unknown>;
  const kb = (report.knowledge_analysis ?? {}) as Record<string, unknown>;
  const stale = (kb.stale_topics ?? []) as string[];
  const topicAges = (kb.knowledge_topic_ages_days ?? {}) as Record<string, number>;

  const rows = KB_TOPICS_DEFAULT.map(({ topic, key, days }) => {
    const age = topicAges[key] ?? days;
    const isStale = stale.includes(key) || age >= 60;
    return {
      topic,
      updated: `${age}d ago`,
      status: isStale ? "stale" : "healthy",
    };
  });

  return (
    <>
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
            Unknown intent proxy: {String(metrics.negative_feedback_rate ?? "—")}
          </li>
        </ul>
      </CardStatic>

      <CardStatic>
        <h3 className="mb-4 text-sm font-medium">Knowledge base health</h3>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wider text-muted">
              <th className="pb-2 font-medium">Topic</th>
              <th className="pb-2 font-medium">Last updated</th>
              <th className="pb-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.topic} className="border-b border-border/40">
                <td className="py-2">{r.topic}</td>
                <td className="py-2 text-muted">{r.updated}</td>
                <td className="py-2">
                  <span
                    className={
                      r.status === "stale" ? "text-warning" : "text-success"
                    }
                  >
                    {r.status}
                  </span>
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
            diagnosis.root_cause ??
              diagnosis.diagnosis ??
              "Failures may originate from stale API documentation rather than statistical drift."
          )}
        </p>
      </CardStatic>
    </>
  );
}
