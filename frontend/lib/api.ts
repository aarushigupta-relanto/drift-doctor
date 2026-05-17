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
