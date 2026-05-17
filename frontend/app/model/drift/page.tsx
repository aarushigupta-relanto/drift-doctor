"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ModelMetrics } from "@/components/dashboard/ModelMetrics";
import { ModelDriftPanel } from "@/components/dashboard/ModelDriftPanel";

export default function ModelDriftPage() {
  return (
    <DashboardLayout
      basePath="/model"
      mode="model"
      systemType="predictive_model"
      title="Drift analysis"
      metrics={<ModelMetrics />}
    >
      <ModelDriftPanel />
    </DashboardLayout>
  );
}
