"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ReportView } from "@/components/dashboard/ReportView";

export default function ModelReportPage() {
  return (
    <DashboardLayout
      basePath="/model"
      mode="model"
      systemType="predictive_model"
      title="Drift report"
    >
      <ReportView systemType="predictive_model" />
    </DashboardLayout>
  );
}
