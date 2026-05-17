"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ReportView } from "@/components/dashboard/ReportView";

export default function ChatbotReportPage() {
  return (
    <DashboardLayout
      basePath="/chatbot"
      mode="chatbot"
      systemType="chatbot"
      title="Drift report"
    >
      <ReportView systemType="chatbot" />
    </DashboardLayout>
  );
}
