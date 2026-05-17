"use client";

import { useDriftView } from "@/hooks/useDriftView";
import { DriftChip } from "@/components/ui/Tooltip";
import { CardStatic } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { EmptyState } from "./EmptyState";
import type { SystemType } from "@/lib/api";

function severityAlert(s?: string) {
  if (s === "HIGH") return "high" as const;
  if (s === "MEDIUM") return "medium" as const;
  return "low" as const;
}

export function ReportView({ systemType }: { systemType: SystemType }) {
  const v = useDriftView();
  const { report, diagnosis } = v;
  const isChatbot = systemType === "chatbot";
  const affected = (diagnosis.affected_features ?? []) as string[];
  const actions = (diagnosis.recommended_action ?? []) as string[];
  const kb = report.knowledge_analysis as Record<string, unknown> | undefined;
  const staleTopics = (kb?.stale_topics ?? []) as string[];

  if (!v.hasData) {
    return <EmptyState systemType={systemType} />;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-xl font-medium">Drift report</h2>
        <p className="mt-1 text-sm text-muted">
          Structured incident summary from the latest monitoring run.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Mini label="System type" value={String(report.system_type ?? systemType)} />
        <Mini label="Source" value={String(diagnosis.classification_source ?? "user_input")} />
        <Mini label="Operational severity" value={v.operationalSeverity} />
        <Mini label="Production risk" value={v.productionRisk} />
        <Mini label="Retraining" value={v.retrainingStatus} />
        <Mini label="Drift detected" value={report.drift_detected ? "Yes" : "No"} />
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <MetricCard label="PSI" value={String(v.psiScore)} glossaryKey="psi_score" />
        <MetricCard label="Confidence" value={v.confidenceDropPct} glossaryKey="confidence_drop" />
        <MetricCard label="Drift share" value={String(v.driftShare)} glossaryKey="drift_share" />
        <MetricCard
          label="Severity"
          value={v.severity}
          glossaryKey="severity"
          alert={severityAlert(v.severity)}
        />
      </div>

      {v.driftTypes.length > 0 && (
        <CardStatic>
          <h3 className="mb-3 text-xs uppercase tracking-wider text-muted">Drift types</h3>
          <div className="flex flex-wrap gap-2">
            {v.driftTypes.map((t) => (
              <DriftChip key={t} type={t} />
            ))}
          </div>
        </CardStatic>
      )}

      <CardStatic className="space-y-4">
        <Section title="Diagnosis" text={String(diagnosis.diagnosis ?? "—")} />
        <Section title="Root cause" text={String(diagnosis.root_cause ?? "—")} />
        <Section title="Recommendation" text={String(diagnosis.recommendation ?? "—")} />
        <div className="flex flex-wrap gap-4 text-sm">
          <span>
            <span className="text-muted">Urgency: </span>
            {String(diagnosis.urgency ?? "—")}
          </span>
          <span>
            <span className="text-muted">Confidence: </span>
            {String(diagnosis.confidence ?? "—")}
          </span>
        </div>
      </CardStatic>

      {affected.length > 0 && (
        <CardStatic>
          <h3 className="mb-3 text-xs uppercase tracking-wider text-muted">Affected features</h3>
          <ol className="space-y-2">
            {affected.map((f, i) => (
              <li key={f} className="flex items-center gap-3 border-b border-border/50 pb-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#1a1a1a] text-xs text-muted">
                  {i + 1}
                </span>
                <span className="text-sm">{f}</span>
              </li>
            ))}
          </ol>
        </CardStatic>
      )}

      {isChatbot && staleTopics.length > 0 && (
        <CardStatic>
          <h3 className="mb-2 text-xs uppercase tracking-wider text-muted">Stale knowledge</h3>
          <ul className="space-y-1 text-sm text-muted">
            {staleTopics.map((t) => (
              <li key={t}>{String(t).replace(/_/g, " ")}</li>
            ))}
          </ul>
        </CardStatic>
      )}

      {actions.length > 0 && (
        <CardStatic>
          <h3 className="mb-3 text-xs uppercase tracking-wider text-muted">Recommended actions</h3>
          <div className="space-y-2">
            {actions.map((a) => (
              <div key={a} className="rounded-lg border border-border bg-[#0f0f0f] px-3 py-2">
                <p className="text-sm font-medium">{a}</p>
              </div>
            ))}
          </div>
        </CardStatic>
      )}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className="truncate text-sm font-medium">{value}</p>
    </div>
  );
}

function Section({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h4 className="mb-1 text-xs uppercase tracking-wider text-muted">{title}</h4>
      <p className="text-sm leading-relaxed text-white/90">{text}</p>
    </div>
  );
}
