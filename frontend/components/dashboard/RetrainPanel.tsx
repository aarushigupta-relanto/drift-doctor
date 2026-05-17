"use client";

import { useCallback, useEffect, useState } from "react";
import { useDriftView } from "@/hooks/useDriftView";
import { CardStatic } from "@/components/ui/Card";
import { DriftChip } from "@/components/ui/Tooltip";
import { EmptyState } from "./EmptyState";
import type { SystemType } from "@/lib/api";
import {
  fetchRetrainHistory,
  fetchRetrainStatus,
  triggerRetrain,
  type RetrainResult,
  type RetrainTaskStatus,
} from "@/lib/api";

function pct(n: number | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <p className="text-sm">
      <span className="text-muted">{label}: </span>
      <span className="text-white">{value}</span>
    </p>
  );
}

export function RetrainPanel({ systemType }: { systemType: SystemType }) {
  const v = useDriftView();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [result, setResult] = useState<RetrainResult | null>(null);
  const [history, setHistory] = useState<RetrainTaskStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    const data = await fetchRetrainHistory(8);
    setHistory(data.runs ?? []);
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (!taskId || status === "completed" || status === "failed") return;
    const t = setInterval(async () => {
      try {
        const s = await fetchRetrainStatus(taskId);
        setStatus(s.status);
        setProgress(s.progress ?? null);
        if (s.status === "completed" || s.status === "failed") {
          setResult((s.result as RetrainResult) ?? null);
          loadHistory();
        }
      } catch {
        /* ignore poll errors */
      }
    }, 1500);
    return () => clearInterval(t);
  }, [taskId, status, loadHistory]);

  const onTrigger = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await triggerRetrain({
        drift_types: v.driftTypes,
        requested_by: systemType,
      });
      setTaskId(res.task_id);
      setStatus(res.status);
      setProgress("Queued");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retrain failed");
    } finally {
      setLoading(false);
    }
  };

  if (!v.hasData && systemType === "chatbot") {
    return <EmptyState systemType={systemType} />;
  }

  const deploy = result?.deployment_recommendation;
  const val = result?.validation_metrics;
  const train = result?.training_metrics;
  const window = result?.training_window;

  return (
    <div className="space-y-6 max-w-4xl">
      <CardStatic>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-medium">Training status</h3>
          <button
            type="button"
            disabled={loading || status === "running" || status === "queued"}
            onClick={onTrigger}
            className="rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-white/90 disabled:opacity-50"
          >
            {loading || status === "running" ? "Retraining…" : "Trigger retrain"}
          </button>
        </div>
        {error && <p className="mb-2 text-sm text-red-400">{error}</p>}
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <MetricRow label="Task" value={taskId ?? "—"} />
          <MetricRow label="Status" value={status ?? "idle"} />
          <MetricRow label="Progress" value={progress ?? "—"} />
          <MetricRow label="Strategy" value={result?.strategy ?? String(v.retrainStrategy)} />
        </div>
        {systemType === "chatbot" && (
          <p className="mt-3 text-xs text-muted">
            Chatbot KB drift may resolve via knowledge refresh; classifier retrain still runs
            when statistical drift is present.
          </p>
        )}
      </CardStatic>

      <div className="grid gap-6 lg:grid-cols-2">
        <CardStatic>
          <h3 className="mb-3 text-sm font-medium">Detected drift types</h3>
          <div className="mb-4 flex flex-wrap gap-2">
            {v.driftTypes.length ? (
              v.driftTypes.map((t) => <DriftChip key={t} type={t} />)
            ) : (
              <p className="text-sm text-muted">No drift types in last report.</p>
            )}
          </div>
          <MetricRow label="Production risk" value={v.productionRisk} />
          <MetricRow label="Retraining necessity" value={v.retrainingStatus} />
        </CardStatic>

        <CardStatic>
          <h3 className="mb-3 text-sm font-medium">Candidate model metrics</h3>
          {result?.training_skipped ? (
            <p className="text-sm text-muted">Training skipped (knowledge refresh strategy).</p>
          ) : train ? (
            <div className="space-y-1">
              <MetricRow label="Model artifact" value={result?.candidate_model ?? "—"} />
              <MetricRow label="Train accuracy" value={pct(train.accuracy)} />
              <MetricRow label="Train F1" value={pct(train.f1)} />
              <MetricRow label="Train samples" value={String(train.n_train ?? "—")} />
            </div>
          ) : (
            <p className="text-sm text-muted">Run retrain to train a candidate model.</p>
          )}
        </CardStatic>
      </div>

      <CardStatic>
        <h3 className="mb-3 text-sm font-medium">
          Validation comparison (production window: clean_web)
        </h3>
        {val ? (
          <>
            <p className="mb-3 text-xs leading-relaxed text-muted">
              {(val as { validation_note?: string }).validation_note ??
                "Compares deployed vs candidate on simulated production traffic (clean_web)."}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <MetricRow
                label="Deployed accuracy (production window)"
                value={pct(val.old_accuracy)}
              />
              <MetricRow
                label="Candidate accuracy (production window)"
                value={pct(val.new_accuracy)}
              />
              <MetricRow label="Accuracy delta" value={pct(val.improvement)} />
              <MetricRow label="F1 delta" value={pct(val.f1_delta)} />
              <MetricRow label="Precision delta" value={pct(val.precision_delta)} />
              <MetricRow label="Recall delta" value={pct(val.recall_delta)} />
            </div>
            {(val as { baseline_validation?: { deployed_accuracy?: number; deployed_f1?: number } })
              .baseline_validation && (
              <div className="mt-4 rounded-lg border border-border bg-[#0f0f0f] p-3">
                <p className="mb-2 text-xs font-medium text-white/80">
                  Deployed model on historical baseline (clean)
                </p>
                <MetricRow
                  label="Deployed accuracy"
                  value={pct(
                    (val as { baseline_validation?: { deployed_accuracy?: number } })
                      .baseline_validation?.deployed_accuracy
                  )}
                />
                <MetricRow
                  label="Deployed F1"
                  value={pct(
                    (val as { baseline_validation?: { deployed_f1?: number } })
                      .baseline_validation?.deployed_f1
                  )}
                />
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-muted">Validation runs on simulated production window (clean_web).</p>
        )}
      </CardStatic>

      <CardStatic>
        <h3 className="mb-3 text-sm font-medium">Deployment recommendation</h3>
        {deploy ? (
          <div className="space-y-2">
            <p className="text-lg font-medium text-white">{deploy.decision}</p>
            {deploy.confidence != null && (
              <MetricRow label="Confidence" value={pct(deploy.confidence)} />
            )}
            <p className="text-sm leading-relaxed text-white/85">{deploy.reason}</p>
          </div>
        ) : result?.error ? (
          <p className="text-sm text-red-400">{result.error}</p>
        ) : (
          <p className="text-sm text-muted">Awaiting validation results.</p>
        )}
      </CardStatic>

      {window && (
        <CardStatic>
          <h3 className="mb-3 text-sm font-medium">Training data window</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            <MetricRow
              label="Historical (clean)"
              value={String(window.historical_samples ?? "—")}
            />
            <MetricRow
              label="Production (clean_web)"
              value={String(window.production_samples ?? "—")}
            />
            {window.training_samples != null && (
              <MetricRow label="Training rows" value={String(window.training_samples)} />
            )}
            {window.strategy != null && (
              <MetricRow label="Applied strategy" value={String(window.strategy)} />
            )}
          </div>
        </CardStatic>
      )}

      <CardStatic>
        <h3 className="mb-3 text-sm font-medium">Historical retraining runs</h3>
        {history.length === 0 ? (
          <p className="text-sm text-muted">No prior runs.</p>
        ) : (
          <ul className="space-y-2">
            {history.map((run) => {
              const r = run.result as RetrainResult | undefined;
              return (
                <li
                  key={run.task_id}
                  className="rounded-lg border border-border bg-[#0f0f0f] px-3 py-2 text-xs"
                >
                  <p className="text-white/90">
                    {run.created_at?.slice(0, 19) ?? run.task_id} — {run.status}
                    {r?.strategy ? ` (${r.strategy})` : ""}
                  </p>
                  <p className="text-muted">
                    {r?.deployment_recommendation?.decision ??
                      r?.recommendation ??
                      run.progress ??
                      "—"}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </CardStatic>
    </div>
  );
}
