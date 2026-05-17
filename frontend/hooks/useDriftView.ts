import { useDriftStore } from "@/lib/store";
import { buildChatbotMetrics, buildDriftView } from "@/lib/drift-selectors";

export function useDriftView() {
  const latest = useDriftStore((s) => s.latest);
  return buildDriftView(latest);
}

export function useChatbotMetrics() {
  const latest = useDriftStore((s) => s.latest);
  const report = (latest?.report ?? {}) as Record<string, unknown>;
  return buildChatbotMetrics(report);
}
