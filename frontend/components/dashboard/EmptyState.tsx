"use client";

import { useDriftStore } from "@/lib/store";
import type { SystemType } from "@/lib/api";

export function EmptyState({ systemType }: { systemType: SystemType }) {
  const runMonitor = useDriftStore((s) => s.runMonitor);
  const loading = useDriftStore((s) => s.loading);

  return (
    <div className="rounded-xl border border-dashed border-border bg-card/50 px-8 py-12 text-center">
      <p className="text-sm text-muted">
        No drift data loaded yet. Run monitoring to populate this dashboard.
      </p>
      <button
        type="button"
        disabled={loading}
        onClick={() => runMonitor(systemType)}
        className="mt-4 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-black hover:bg-white/90 disabled:opacity-50"
      >
        Run monitoring now
      </button>
      {systemType === "predictive_model" && (
        <p className="mt-3 text-xs text-muted">
          Requires <code className="text-white/80">final_dataset.csv</code> and
          trained models under <code className="text-white/80">ml/models/</code>.
          Chatbot mode works with simulated data out of the box.
        </p>
      )}
    </div>
  );
}
