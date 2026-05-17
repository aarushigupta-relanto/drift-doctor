"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Copilot } from "@/components/dashboard/Copilot";

export default function ChatbotCopilotPage() {
  return (
    <DashboardLayout
      basePath="/chatbot"
      mode="chatbot"
      systemType="chatbot"
      title="AI assistant"
    >
      <div className="mx-auto max-w-2xl">
        <Copilot mode="chatbot" />
      </div>
    </DashboardLayout>
  );
}
