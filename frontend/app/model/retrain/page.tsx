"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ModelMetrics } from "@/components/dashboard/ModelMetrics";
import { RetrainPanel } from "@/components/dashboard/RetrainPanel";

export default function ModelRetrainPage() {
  return (
    <DashboardLayout
      basePath="/model"
      mode="model"
      systemType="predictive_model"
      title="Retraining"
      metrics={<ModelMetrics />}
    >
      <RetrainPanel systemType="predictive_model" />
    </DashboardLayout>
  );
}
