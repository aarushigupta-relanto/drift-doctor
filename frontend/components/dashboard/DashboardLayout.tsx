"use client";

import { useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { useDriftStore } from "@/lib/store";
import type { SystemType } from "@/lib/api";
import { RefreshCw, Loader2 } from "lucide-react";

export function DashboardLayout({
  basePath,
  mode,
  systemType,
  title,
  metrics,
  children,
}: {
  basePath: "/model" | "/chatbot";
  mode: "model" | "chatbot";
  systemType: SystemType;
  title: string;
  metrics?: React.ReactNode;
  children: React.ReactNode;
}) {
  const runMonitor = useDriftStore((s) => s.runMonitor);
  const loading = useDriftStore((s) => s.loading);
  const error = useDriftStore((s) => s.error);
  const backendOnline = useDriftStore((s) => s.backendOnline);
  const setSystemType = useDriftStore((s) => s.setSystemType);
  const loadLatest = useDriftStore((s) => s.loadLatest);

  useEffect(() => {
    setSystemType(systemType);
    loadLatest();
  }, [systemType, setSystemType, loadLatest]);

  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar basePath={basePath} />
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h1 className="text-lg font-medium tracking-tight">{title}</h1>
            <p className="text-sm text-muted">
              Production observability · {systemType}
              {!backendOnline && (
                <span className="ml-2 text-warning">· backend offline</span>
              )}
            </p>
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={() => runMonitor(systemType)}
            className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm transition hover:border-white/30 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Run monitoring
          </button>
        </header>

        {error && (
          <p className="border-b border-alert/30 bg-alert/10 px-6 py-2 text-sm text-alert">
            {error}
          </p>
        )}

        {metrics && (
          <section className="grid grid-cols-2 gap-3 border-b border-border px-6 py-4 lg:grid-cols-4">
            {metrics}
          </section>
        )}

        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </main>
    </div>
  );
}
