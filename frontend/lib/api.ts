const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SystemType = "predictive_model" | "chatbot";

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch(
  url: string,
  init?: RequestInit
): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new ApiError(
      "Cannot reach the backend. Start it on port 8000 (uvicorn backend.main:app)."
    );
  }
}

export async function fetchLatestDrift() {
  const res = await apiFetch(`${API_BASE}/api/drift/latest`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) return null;
  const data = await res.json();
  if (!data || data.message) return null;
  return data;
}

export async function fetchDriftHistory(limit = 20) {
  const res = await apiFetch(`${API_BASE}/api/drift/history?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

export async function runMonitoring(payload: {
  system_type: SystemType;
  use_simulated_chatbot?: boolean;
  explain?: boolean;
  persist?: boolean;
  records?: unknown[];
}) {
  const res = await apiFetch(`${API_BASE}/api/monitor/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      explain: true,
      persist: true,
      ...payload,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(", ")
          : `Monitor failed (${res.status})`;
    throw new ApiError(msg, res.status);
  }
  return res.json();
}

export async function postDriftReport(report: Record<string, unknown>) {
  const res = await apiFetch(`${API_BASE}/api/drift/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  if (!res.ok) throw new ApiError(`Report failed (${res.status})`, res.status);
  return res.json();
}

export async function sendChat(message: string) {
  const res = await apiFetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new ApiError(`Chat failed (${res.status})`, res.status);
  return res.json();
}

export function getWsUrl() {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws`;
}

export type RetrainResult = {
  status?: string;
  strategy?: string;
  strategy_reason?: string;
  candidate_model?: string;
  training_metrics?: {
    accuracy?: number;
    precision?: number;
    recall?: number;
    f1?: number;
    n_train?: number;
    n_val?: number;
  };
  training_window?: Record<string, unknown>;
  validation_metrics?: {
    old_accuracy?: number;
    new_accuracy?: number;
    improvement?: number;
    precision_delta?: number;
    recall_delta?: number;
    f1_delta?: number;
  };
  deployment_recommendation?: {
    decision?: string;
    confidence?: number;
    reason?: string;
  };
  recommendation?: string;
  training_skipped?: boolean;
  error?: string;
};

export type RetrainTaskStatus = {
  task_id: string;
  status: string;
  strategy?: string;
  progress?: string;
  result?: RetrainResult | null;
  created_at?: string;
};

export async function triggerRetrain(payload?: {
  strategy?: string;
  drift_types?: string[];
  requested_by?: string;
}) {
  const res = await apiFetch(`${API_BASE}/api/retrain/trigger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(
      typeof err.detail === "string" ? err.detail : `Retrain failed (${res.status})`,
      res.status
    );
  }
  return res.json() as Promise<{ task_id: string; status: string; message: string }>;
}

export async function fetchRetrainStatus(taskId: string) {
  const res = await apiFetch(`${API_BASE}/api/retrain/status/${taskId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(`Status failed (${res.status})`, res.status);
  return res.json() as Promise<RetrainTaskStatus>;
}

export async function fetchRetrainHistory(limit = 10) {
  const res = await apiFetch(`${API_BASE}/api/retrain/history?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) return { runs: [] };
  return res.json() as Promise<{ runs: RetrainTaskStatus[] }>;
}
