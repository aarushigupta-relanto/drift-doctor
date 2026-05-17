"use client";

import { MetricCard } from "@/components/ui/MetricCard";
import { useDriftView } from "@/hooks/useDriftView";

export function ModelMetrics() {
  const v = useDriftView();
  const sevAlert =
    v.severity === "HIGH"
      ? "high"
      : v.severity === "MEDIUM"
        ? "medium"
        : "low";

  const dropNum = parseInt(v.confidenceDropPct, 10);

  return (
    <>
      <MetricCard
        label="Drift severity"
        value={v.severity}
        glossaryKey="severity"
        alert={v.hasData ? sevAlert : "none"}
      />
      <MetricCard
        label="PSI score"
        value={String(v.psiScore)}
        glossaryKey="psi_score"
        alert={Number(v.psiScore) > 0.4 ? "high" : "none"}
      />
      <MetricCard
        label="Confidence drop"
        value={v.confidenceDropPct}
        glossaryKey="confidence_drop"
        trend={!Number.isNaN(dropNum) && dropNum < 0 ? "down" : "flat"}
        alert={!Number.isNaN(dropNum) && dropNum < -20 ? "high" : "none"}
      />
      <MetricCard
        label="Retraining status"
        value={v.retrainingStatus}
        sub={v.retrainStrategy}
      />
    </>
  );
}
