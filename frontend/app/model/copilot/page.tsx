"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Copilot } from "@/components/dashboard/Copilot";

export default function ModelCopilotPage() {
  return (
    <DashboardLayout
      basePath="/model"
      mode="model"
      systemType="predictive_model"
      title="AI assistant"
    >
      <div className="mx-auto max-w-2xl">
        <Copilot mode="model" />
      </div>
    </DashboardLayout>
  );
}
