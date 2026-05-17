"use client";

import { useDriftView } from "@/hooks/useDriftView";
import { CardStatic } from "@/components/ui/Card";
import { DriftTimeline } from "./DriftTimeline";
import { EmptyState } from "./EmptyState";

export function ModelDriftPanel() {
  const v = useDriftView();
  const features = [
    "confidence",
    "intent_distribution",
    "vocabulary_shift",
    "distribution_drift",
  ];

  if (!v.hasData) return <EmptyState systemType="predictive_model" />;

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-2">
        <DriftTimeline />
        <CardStatic>
          <h3 className="mb-4 text-sm font-medium">Drifted features</h3>
          <ul className="space-y-3">
            {features.map((f) => (
              <li
                key={f}
                className="flex items-center justify-between border-b border-border/50 pb-2 text-sm"
              >
                <span>{f}</span>
                <span className="text-xs text-muted">
                  {f === "confidence"
                    ? `KS p=${v.confidence.p_value ?? "—"} · drifted=${v.confidence.drifted ? "yes" : "no"}`
                    : f === "intent_distribution"
                      ? ((v.intents.top_shifted_intents as string[]) ?? []).join(", ") || "—"
                      : `share ${v.driftShare}`}
                </span>
              </li>
            ))}
          </ul>
        </CardStatic>
      </section>
      <CardStatic>
        <h3 className="mb-2 text-sm font-medium">Distribution summary</h3>
        <p className="text-sm text-muted">
          Unknown intents: ref {(Number(v.intents.unknown_pct_reference) * 100).toFixed(0)}% → cur{" "}
          {(Number(v.intents.unknown_pct_current) * 100).toFixed(0)}%
        </p>
      </CardStatic>
    </div>
  );
}
