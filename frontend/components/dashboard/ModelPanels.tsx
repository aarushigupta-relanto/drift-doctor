"use client";

import { useDriftStore } from "@/lib/store";
import { CardStatic } from "@/components/ui/Card";
import { DriftTimeline } from "./DriftTimeline";
import { DriftChip } from "@/components/ui/Tooltip";

export function ModelPanels() {
  const latest = useDriftStore((s) => s.latest);
  const report = (latest?.report ?? {}) as Record<string, unknown>;
  const diagnosis = (latest?.diagnosis ?? {}) as Record<string, unknown>;
  const driftTypes = (report.drift_types ?? diagnosis.drift_types ?? []) as string[];
  const details = (report.details ?? {}) as Record<string, Record<string, unknown>>;
  const intents = details.intent_distribution ?? {};

  const features = [
    "confidence",
    "intent_distribution",
    "vocabulary_shift",
    "distribution_drift",
  ];

  return (
  <>
    <section id="drift" className="grid gap-6 lg:grid-cols-2">
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
              <span className="text-muted text-xs">
                {f === "confidence" && details.confidence
                  ? `KS p=${details.confidence.p_value ?? "—"}`
                  : f === "intent_distribution"
                    ? (intents.top_shifted_intents as string[])?.join(", ") || "—"
                    : "monitored"}
              </span>
            </li>
          ))}
        </ul>
      </CardStatic>
    </section>

    <section id="retrain" className="grid gap-6 lg:grid-cols-2">
      <CardStatic>
        <h3 className="mb-4 text-sm font-medium">Retraining strategy</h3>
        <div className="mb-4 flex flex-wrap gap-2">
          {driftTypes.length ? driftTypes.map((t) => <DriftChip key={t} type={t} />) : (
            <p className="text-sm text-muted">Run monitoring to detect drift types.</p>
          )}
        </div>
        <p className="text-sm text-muted">
          <span className="text-white">Strategy: </span>
          {String(diagnosis.retrain_strategy ?? diagnosis.retraining_necessity ?? "—")}
        </p>
        <p className="mt-2 text-sm text-muted">
          <span className="text-white">Production risk: </span>
          {String(diagnosis.production_risk ?? "—")}
        </p>
      </CardStatic>
      <CardStatic>
        <h3 className="mb-3 text-sm font-medium">Incident summary</h3>
        <p className="text-sm leading-relaxed text-white/90">
          {String(diagnosis.diagnosis ?? "No diagnosis yet. Click Run monitoring to analyze production drift.")}
        </p>
      </CardStatic>
    </section>
  </>
  );
}
