"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ChatbotMetrics } from "@/components/dashboard/ChatbotMetrics";
import { RetrainPanel } from "@/components/dashboard/RetrainPanel";

export default function ChatbotRetrainPage() {
  return (
    <DashboardLayout
      basePath="/chatbot"
      mode="chatbot"
      systemType="chatbot"
      title="Retraining"
      metrics={<ChatbotMetrics />}
    >
      <RetrainPanel systemType="chatbot" />
    </DashboardLayout>
  );
}
