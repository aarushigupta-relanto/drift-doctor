"use client";

import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { ChatbotMetrics } from "@/components/dashboard/ChatbotMetrics";
import { CardStatic } from "@/components/ui/Card";
import { useDriftView } from "@/hooks/useDriftView";
import { EmptyState } from "@/components/dashboard/EmptyState";

export default function ChatbotOverviewPage() {
  const v = useDriftView();

  return (
    <DashboardLayout
      basePath="/chatbot"
      mode="chatbot"
      systemType="chatbot"
      title="Overview"
      metrics={<ChatbotMetrics />}
    >
      {!v.hasData ? (
        <EmptyState systemType="chatbot" />
      ) : (
        <CardStatic>
          <h3 className="mb-3 text-sm font-medium">Operational summary</h3>
          <p className="text-sm leading-relaxed text-white/90">
            {String(v.diagnosis.diagnosis ?? "Chatbot monitoring complete.")}
          </p>
        </CardStatic>
      )}
    </DashboardLayout>
  );
}
