export type DriftTypeInfo = {
  label: string;
  meaning: string;
  triggeredBy: string[];
  impact: string[];
};

export const DRIFT_TYPE_GLOSSARY: Record<string, DriftTypeInfo> = {
  confidence_drift: {
    label: "confidence_drift",
    meaning:
      "Model confidence has degraded significantly relative to the reference baseline.",
    triggeredBy: ["mean_cur_confidence drop", "KS statistical drift"],
    impact: ["unreliable predictions", "increased uncertainty"],
  },
  confidence_degradation: {
    label: "confidence_degradation",
    meaning: "Live routing confidence is falling on production queries.",
    triggeredBy: ["avg_confidence vs reference", "negative feedback correlation"],
    impact: ["misrouted intents", "fallback-heavy sessions"],
  },
  confidence_collapse: {
    label: "confidence_collapse",
    meaning: "Sharp collapse in model confidence across the monitoring window.",
    triggeredBy: ["avg_confidence < 0.55", "reference gap > 0.15"],
    impact: ["critical production reliability risk"],
  },
  distribution_drift: {
    label: "distribution_drift",
    meaning: "Production feature or score distributions diverged from reference.",
    triggeredBy: ["Evidently drift_share", "PSI elevation"],
    impact: ["calibration drift", "segment performance skew"],
  },
  psi_instability: {
    label: "psi_instability",
    meaning: "Population Stability Index indicates score distribution shift.",
    triggeredBy: ["psi_score > 0.25"],
    impact: ["ranking instability", "threshold breaches"],
  },
  feature_instability: {
    label: "feature_instability",
    meaning: "Monitored input features show significant production shift.",
    triggeredBy: ["drift_share > 0.3"],
    impact: ["feature pipeline review required"],
  },
  intent_drift: {
    label: "intent_drift",
    meaning: "New or shifting user intents appear in production traffic.",
    triggeredBy: ["unknown intent growth", "intent distribution shift"],
    impact: ["coverage gaps", "misclassification"],
  },
  behavioral_drift: {
    label: "behavioral_drift",
    meaning: "User interaction patterns changed vs historical baseline.",
    triggeredBy: ["top_shifted_intents", "session pattern change"],
    impact: ["policy/routing mismatch"],
  },
  conversational_drift: {
    label: "conversational_drift",
    meaning: "Conversational style and phrasing patterns have shifted.",
    triggeredBy: ["greeting/FAQ rate change", "query length shift"],
    impact: ["RAG recall mismatch", "tone misalignment"],
  },
  vocabulary_drift: {
    label: "vocabulary_drift",
    meaning: "Users phrase requests with vocabulary absent from training.",
    triggeredBy: ["Jaccard vocabulary distance", "drift_share on text"],
    impact: ["embedding recall degradation"],
  },
  semantic_drift: {
    label: "semantic_drift",
    meaning: "Semantic query distribution moved away from reference embeddings.",
    triggeredBy: ["vocabulary_drift_score", "embedding distance"],
    impact: ["retrieval precision loss"],
  },
  possible_knowledge_staleness: {
    label: "possible_knowledge_staleness",
    meaning:
      "Failures may originate from stale retrieval or outdated knowledge content.",
    triggeredBy: ["stale topic hits", "low PSI + poor responses"],
    impact: ["incorrect answers without model retrain"],
  },
  stale_knowledge_suspicion: {
    label: "stale_knowledge_suspicion",
    meaning: "Implicated KB topics exceed freshness SLA.",
    triggeredBy: ["topic age > threshold", "query-topic mapping"],
    impact: ["refresh embeddings/docs over retraining"],
  },
  retrieval_degradation: {
    label: "retrieval_degradation",
    meaning: "Elevated fallback responses suggest retrieval pipeline failure.",
    triggeredBy: ["fallback_response_rate", "generic answers"],
    impact: ["stale chunks", "missing documents"],
  },
  retrieval_suspicion: {
    label: "retrieval_suspicion",
    meaning: "Statistical drift is low but answers degrade — suspect retrieval.",
    triggeredBy: ["stable PSI + poor feedback"],
    impact: ["audit vector index"],
  },
  hallucination_suspicion: {
    label: "hallucination_suspicion",
    meaning: "Low confidence paired with confident-sounding generic answers.",
    triggeredBy: ["fallback + low confidence", "negative feedback"],
    impact: ["guardrails", "grounding review"],
  },
  response_quality_degradation: {
    label: "response_quality_degradation",
    meaning: "Response usefulness declined per feedback and heuristics.",
    triggeredBy: ["negative_feedback_rate", "low-information responses"],
    impact: ["CSAT risk", "escalation volume"],
  },
};

export type MetricInfo = {
  label: string;
  definition: string;
  normalRange: string;
  whyItMatters: string;
};

export const METRIC_GLOSSARY: Record<string, MetricInfo> = {
  psi_score: {
    label: "PSI Score",
    definition:
      "Population Stability Index measures production distribution drift vs reference traffic.",
    normalRange: "< 0.2 stable, 0.2–0.4 watch, > 0.4 critical",
    whyItMatters: "High PSI implies scoring or feature distributions have shifted materially.",
  },
  drift_share: {
    label: "Drift Share",
    definition: "Share of monitored features or text columns flagged as drifted.",
    normalRange: "< 0.2 stable, > 0.3 elevated",
    whyItMatters: "Indicates breadth of production shift across the monitoring surface.",
  },
  confidence_drop: {
    label: "Confidence Drop",
    definition: "Reference mean confidence minus current mean confidence.",
    normalRange: "< 10% typical, > 30% critical",
    whyItMatters: "Signals model uncertainty or routing instability on live traffic.",
  },
  severity: {
    label: "Drift Severity",
    definition: "Composite operational severity from monitoring rules.",
    normalRange: "LOW / MEDIUM / HIGH",
    whyItMatters: "Drives incident priority and remediation urgency.",
  },
  negative_feedback: {
    label: "Negative Feedback Rate",
    definition: "Share of sessions with explicit negative user feedback.",
    normalRange: "< 15% healthy, > 25% elevated",
    whyItMatters: "Direct signal of conversational quality regression.",
  },
  knowledge_freshness: {
    label: "Knowledge Freshness",
    definition: "Simulated age of implicated knowledge topics vs SLA.",
    normalRange: "Topics updated within 60 days",
    whyItMatters: "Stale docs cause retrieval failures without statistical model drift.",
  },
};

export const KB_TOPICS_DEFAULT = [
  { topic: "API Docs", key: "api_docs", days: 200 },
  { topic: "Pricing", key: "pricing", days: 90 },
  { topic: "Refund Policy", key: "refund_policy", days: 120 },
  { topic: "Shipping", key: "shipping", days: 10 },
];
