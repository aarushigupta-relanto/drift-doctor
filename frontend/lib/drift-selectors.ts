import type { DriftEvent } from "./store";

export type DriftView = {
  report: Record<string, unknown>;
  diagnosis: Record<string, unknown>;
  operational: Record<string, unknown>;
  remediation: Record<string, unknown>;
  details: Record<string, Record<string, unknown>>;
  confidence: Record<string, unknown>;
  intents: Record<string, unknown>;
  driftTypes: string[];
  hasData: boolean;
  severity: string;
  psiScore: string;
  driftShare: string;
  confidenceDropPct: string;
  retrainingStatus: string;
  retrainStrategy: string;
  productionRisk: string;
  operationalSeverity: string;
};

function firstString(...values: unknown[]): string | null {
  for (const v of values) {
    if (v == null || v === "") continue;
    const s = String(v).trim();
    if (s && s !== "—") return s;
  }
  return null;
}

function formatRetrainingStatus(value: unknown): string {
  if (value == null || value === "") return "—";
  const s = String(value).toLowerCase();
  if (s === "true" || s === "recommended" || s === "required") {
    return s === "required" ? "REQUIRED" : "RECOMMENDED";
  }
  if (s === "not_required" || s === "false") return "NOT REQUIRED";
  return String(value).toUpperCase();
}

export function buildDriftView(latest: DriftEvent | null): DriftView {
  const report = (latest?.report ?? {}) as Record<string, unknown>;
  const diagnosis = (latest?.diagnosis ?? {}) as Record<string, unknown>;
  const operational = (report.operational_assessment ??
    {}) as Record<string, unknown>;
  const remediation = (report.remediation ?? {}) as Record<string, unknown>;

  const details = (report.details ?? {}) as Record<
    string,
    Record<string, unknown>
  >;
  const confidence = details.confidence ?? {};
  const intents = details.intent_distribution ?? {};

  const meanRef = Number(confidence.mean_ref_confidence ?? 0);
  const meanCur = Number(confidence.mean_cur_confidence ?? 0);
  const dropPct =
    meanRef > 0 || meanCur > 0
      ? `${Math.round((meanCur - meanRef) * 100)}%`
      : "—";

  const driftTypes = (
    (report.drift_types as string[]) ??
    (diagnosis.drift_types as string[]) ??
    []
  ).filter(Boolean);

  const hasData = Boolean(
    latest && (Object.keys(report).length > 0 || latest.severity)
  );

  const retrainingRaw = firstString(
    diagnosis.retraining_necessity,
    report.retraining_necessity,
    operational.retraining_necessity,
    diagnosis.retrain_recommended ? "recommended" : null
  );

  const retrainingStatus = diagnosis.retrain_recommended
    ? "RECOMMENDED"
    : formatRetrainingStatus(retrainingRaw);

  const retrainStrategy =
    firstString(
      diagnosis.retrain_strategy,
      report.retrain_strategy,
      operational.recommended_strategy,
      remediation.primary_action
    ) ?? "—";

  const productionRisk =
    firstString(
      diagnosis.production_risk,
      report.production_risk,
      operational.production_risk,
      operational.production_distribution_mismatch
        ? "Distribution mismatch detected"
        : null
    ) ?? "—";

  const operationalSeverity =
    firstString(
      diagnosis.operational_severity,
      operational.operational_severity,
      report.severity,
      latest?.severity
    ) ?? "—";

  return {
    report,
    diagnosis,
    operational,
    remediation,
    details,
    confidence,
    intents,
    driftTypes,
    hasData,
    severity: String(report.severity ?? latest?.severity ?? "—"),
    psiScore: report.psi_score != null ? String(report.psi_score) : "—",
    driftShare:
      report.drift_share != null
        ? String(report.drift_share)
        : latest?.drift_share != null
          ? String(latest.drift_share)
          : "—",
    confidenceDropPct: dropPct,
    retrainingStatus,
    retrainStrategy,
    productionRisk,
    operationalSeverity,
  };
}

export function buildChatbotMetrics(report: Record<string, unknown>) {
  const metrics = (report.chatbot_metrics ?? {}) as Record<string, number>;
  const kb = (report.knowledge_analysis ?? {}) as Record<string, unknown>;
  const rq = (report.response_quality ?? {}) as Record<string, boolean>;

  return {
    metrics,
    kb,
    hallucination: rq.hallucination_suspicion ? "ELEVATED" : "LOW",
    kbFresh: kb.possible_knowledge_staleness ? "STALE" : "OK",
    negativeRate:
      metrics.negative_feedback_rate != null
        ? `${Math.round(metrics.negative_feedback_rate * 100)}%`
        : "—",
  };
}
