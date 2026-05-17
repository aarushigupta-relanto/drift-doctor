"use client";

import { MetricCard } from "@/components/ui/MetricCard";
import { useDriftView } from "@/hooks/useDriftView";
import { useChatbotMetrics } from "@/hooks/useDriftView";

export function ChatbotMetrics() {
  const v = useDriftView();
  const c = useChatbotMetrics();

  return (
    <>
      <MetricCard
        label="Conversation drift"
        value={v.severity}
        glossaryKey="severity"
        alert={v.severity === "HIGH" ? "high" : "medium"}
      />
      <MetricCard
        label="Negative feedback"
        value={c.negativeRate}
        glossaryKey="negative_feedback"
        alert={
          c.metrics.negative_feedback_rate != null &&
          c.metrics.negative_feedback_rate > 0.25
            ? "high"
            : "none"
        }
      />
      <MetricCard
        label="Hallucination risk"
        value={c.hallucination}
        alert={c.hallucination === "ELEVATED" ? "high" : "low"}
      />
      <MetricCard
        label="Knowledge freshness"
        value={c.kbFresh}
        glossaryKey="knowledge_freshness"
        alert={c.kbFresh === "STALE" ? "medium" : "low"}
      />
    </>
  );
}
