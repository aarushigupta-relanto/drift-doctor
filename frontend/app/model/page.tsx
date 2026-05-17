"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ModelMetrics } from "@/components/dashboard/ModelMetrics";
import { CardStatic } from "@/components/ui/Card";
import { useDriftView } from "@/hooks/useDriftView";
import { EmptyState } from "@/components/dashboard/EmptyState";

export default function ModelOverviewPage() {
  const v = useDriftView();

  return (
    <DashboardLayout
      basePath="/model"
      mode="model"
      systemType="predictive_model"
      title="Overview"
      metrics={<ModelMetrics />}
    >
      {!v.hasData ? (
        <EmptyState systemType="predictive_model" />
      ) : (
        <CardStatic>
          <h3 className="mb-3 text-sm font-medium">Incident summary</h3>
          <p className="text-sm leading-relaxed text-white/90">
            {String(
              v.diagnosis.diagnosis ??
                "Monitoring complete. Open Drift Report or Drift Analysis for details."
            )}
          </p>
          <p className="mt-3 text-xs text-muted">
            Drift share {String(v.driftShare)} · PSI {String(v.psiScore)} ·{" "}
            {v.driftTypes.length} drift signal(s)
          </p>
        </CardStatic>
      )}
    </DashboardLayout>
  );
}
