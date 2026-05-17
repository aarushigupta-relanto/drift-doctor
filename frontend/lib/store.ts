import { create } from "zustand";
import type { SystemType } from "./api";
import { ApiError, fetchLatestDrift, runMonitoring } from "./api";

export type DriftEvent = {
  id?: number;
  timestamp?: string;
  severity?: string;
  drift_share?: number;
  report?: Record<string, unknown>;
  diagnosis?: Record<string, unknown>;
};

function mergeDiagnosisFromReport(
  report: Record<string, unknown>,
  diagnosis: Record<string, unknown> | null
): Record<string, unknown> | undefined {
  const op = (report.operational_assessment ?? {}) as Record<string, unknown>;
  const remediation = (report.remediation ?? {}) as Record<string, unknown>;
  const merged: Record<string, unknown> = { ...(diagnosis ?? {}) };

  const setIfMissing = (key: string, value: unknown) => {
    if ((merged[key] == null || merged[key] === "") && value != null && value !== "") {
      merged[key] = value;
    }
  };

  setIfMissing("production_risk", report.production_risk ?? op.production_risk);
  setIfMissing(
    "retraining_necessity",
    report.retraining_necessity ?? op.retraining_necessity
  );
  setIfMissing(
    "retrain_strategy",
    report.retrain_strategy ?? op.recommended_strategy ?? remediation.primary_action
  );
  setIfMissing(
    "operational_severity",
    op.operational_severity ?? report.severity
  );

  const necessity = String(merged.retraining_necessity ?? "").toLowerCase();
  if (merged.retrain_recommended == null) {
    merged.retrain_recommended =
      necessity === "required" || necessity === "recommended";
  }

  return Object.keys(merged).length > 0 ? merged : undefined;
}

function normalizeEvent(raw: Record<string, unknown>): DriftEvent {
  const report = (raw.report ?? {}) as Record<string, unknown>;
  const diagnosis = (raw.diagnosis ?? null) as Record<string, unknown> | null;
  const normalizedReport = {
    ...report,
    system_type: report.system_type ?? report.monitoring_mode,
  };

  return {
    id: raw.id as number | undefined,
    timestamp: raw.timestamp as string | undefined,
    severity: (report.severity as string) ?? (raw.severity as string),
    drift_share:
      (report.drift_share as number) ?? (raw.drift_share as number),
    report: normalizedReport,
    diagnosis: mergeDiagnosisFromReport(normalizedReport, diagnosis),
  };
}

type DriftStore = {
  systemType: SystemType | null;
  latest: DriftEvent | null;
  loading: boolean;
  error: string | null;
  backendOnline: boolean;
  setSystemType: (t: SystemType) => void;
  clearError: () => void;
  loadLatest: () => Promise<void>;
  applyEvent: (event: DriftEvent) => void;
  runMonitor: (systemType: SystemType) => Promise<void>;
};

export const useDriftStore = create<DriftStore>((set) => ({
  systemType: null,
  latest: null,
  loading: false,
  error: null,
  backendOnline: true,

  setSystemType: (t) => set({ systemType: t }),
  clearError: () => set({ error: null }),

  loadLatest: async () => {
    try {
      const data = await fetchLatestDrift();
      set({ backendOnline: true });
      if (data) {
        set({ latest: normalizeEvent(data as Record<string, unknown>) });
      }
    } catch (e) {
      if (e instanceof ApiError) {
        set({ backendOnline: false });
      }
      // Do not show banner on silent refresh failure
    }
  },

  applyEvent: (event) => {
    set({
      latest: normalizeEvent({
        id: event.id,
        timestamp: event.timestamp,
        severity: event.severity,
        drift_share: event.drift_share,
        report: event.report,
        diagnosis: event.diagnosis,
      }),
      error: null,
      backendOnline: true,
    });
  },

  runMonitor: async (systemType) => {
    set({ loading: true, error: null, systemType });
    try {
      const result = await runMonitoring({
        system_type: systemType,
        use_simulated_chatbot: systemType === "chatbot",
      });
      set({
        latest: normalizeEvent({
          report: result.report,
          diagnosis: result.diagnosis,
          severity: result.report?.severity,
          drift_share: result.report?.drift_share,
        }),
        backendOnline: true,
        error: null,
      });
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Monitoring failed";
      set({
        error: msg,
        backendOnline: !(e instanceof ApiError && e.message.includes("Cannot reach")),
      });
    } finally {
      set({ loading: false });
    }
  },
}));
