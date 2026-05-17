"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ChatbotMetrics } from "@/components/dashboard/ChatbotMetrics";
import { ChatbotDriftPanel } from "@/components/dashboard/ChatbotDriftPanel";

export default function ChatbotDriftPage() {
  return (
    <DashboardLayout
      basePath="/chatbot"
      mode="chatbot"
      systemType="chatbot"
      title="Drift analysis"
      metrics={<ChatbotMetrics />}
    >
      <ChatbotDriftPanel />
    </DashboardLayout>
  );
}
