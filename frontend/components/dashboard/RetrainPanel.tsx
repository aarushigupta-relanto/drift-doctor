"use client";

import { useDriftView } from "@/hooks/useDriftView";
import { CardStatic } from "@/components/ui/Card";
import { DriftChip } from "@/components/ui/Tooltip";
import { EmptyState } from "./EmptyState";
import type { SystemType } from "@/lib/api";

const ACTIONS_PREDICTIVE = [
  { title: "Full retraining", desc: "Retrain on refreshed production sample when PSI and confidence thresholds are breached." },
  { title: "Distribution rebalancing", desc: "Rebalance training data to match shifted feature distributions." },
  { title: "Refresh production dataset", desc: "Update reference baseline windows before incremental retrain." },
];

const ACTIONS_CHATBOT = [
  { title: "Refresh retrieval knowledge base", desc: "Update stale document embeddings when KB topics exceed freshness SLA." },
  { title: "Refresh embeddings", desc: "Re-embed FAQ and API documentation for shifted query vocabulary." },
  { title: "Targeted conversational fine-tuning", desc: "Fine-tune on clusters with intent drift after KB refresh." },
];

export function RetrainPanel({ systemType }: { systemType: SystemType }) {
  const v = useDriftView();
  const actions = systemType === "chatbot" ? ACTIONS_CHATBOT : ACTIONS_PREDICTIVE;
  const recommended = (v.diagnosis.recommended_action ?? []) as string[];

  if (!v.hasData) return <EmptyState systemType={systemType} />;

  return (
    <div className="space-y-6 max-w-3xl">
      <CardStatic>
        <h3 className="mb-4 text-sm font-medium">Detected drift types</h3>
        <div className="mb-4 flex flex-wrap gap-2">
          {v.driftTypes.length ? (
            v.driftTypes.map((t) => <DriftChip key={t} type={t} />)
          ) : (
            <p className="text-sm text-muted">No drift types in last report.</p>
          )}
        </div>
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <p>
            <span className="text-muted">Strategy: </span>
            <span className="text-white">{v.retrainStrategy}</span>
          </p>
          <p>
            <span className="text-muted">Production risk: </span>
            <span className="text-white">{v.productionRisk}</span>
          </p>
          <p>
            <span className="text-muted">Retraining: </span>
            <span className="text-white">{v.retrainingStatus}</span>
          </p>
          <p>
            <span className="text-muted">Severity: </span>
            <span className="text-white">{v.operationalSeverity}</span>
          </p>
        </div>
      </CardStatic>

      <CardStatic>
        <h3 className="mb-4 text-sm font-medium">Remediation playbook</h3>
        <div className="space-y-3">
          {(recommended.length ? recommended.map((t) => ({ title: t, desc: "Agent-recommended action" })) : actions).map(
            (a) => (
              <div key={a.title} className="rounded-lg border border-border bg-[#0f0f0f] p-4">
                <p className="font-medium text-sm">{a.title}</p>
                <p className="mt-1 text-xs text-muted">{a.desc}</p>
              </div>
            )
          )}
        </div>
      </CardStatic>
    </div>
  );
}
