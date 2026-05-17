"use client";

import { useEffect } from "react";
import { useDriftStore } from "@/lib/store";
import { useWebSocket } from "@/hooks/useWebSocket";

export function Providers({ children }: { children: React.ReactNode }) {
  const loadLatest = useDriftStore((s) => s.loadLatest);
  const applyEvent = useDriftStore((s) => s.applyEvent);

  useWebSocket((msg) => {
    if (msg.type === "drift" && msg.payload) {
      const p = msg.payload as {
        event_id?: number;
        report?: Record<string, unknown>;
        diagnosis?: Record<string, unknown>;
      };
      applyEvent({
        id: p.event_id,
        report: p.report,
        diagnosis: p.diagnosis,
        severity: p.report?.severity as string,
        drift_share: p.report?.drift_share as number,
      });
    }
  });

  useEffect(() => {
    loadLatest();
  }, [loadLatest]);

  return <>{children}</>;
}
