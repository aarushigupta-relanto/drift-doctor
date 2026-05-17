"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Activity,
  RefreshCw,
  MessageSquare,
  FileText,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function Sidebar({ basePath }: { basePath: "/model" | "/chatbot" }) {
  const pathname = usePathname();
  const label = basePath === "/model" ? "Predictive ML" : "Chatbot / RAG";

  const items = [
    { href: basePath, label: "Overview", icon: LayoutDashboard, exact: true },
    { href: `${basePath}/drift`, label: "Drift Analysis", icon: Activity },
    { href: `${basePath}/retrain`, label: "Retraining", icon: RefreshCw },
    { href: `${basePath}/copilot`, label: "AI Assistant", icon: MessageSquare },
    { href: `${basePath}/report`, label: "Drift Report", icon: FileText },
  ];

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-[#0A0A0A] p-4">
      <Link
        href="/"
        className="mb-8 flex items-center gap-2 text-sm text-muted transition hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Home
      </Link>
      <p className="mb-4 text-xs uppercase tracking-widest text-muted">{label}</p>
      <nav className="flex flex-col gap-1">
        {items.map(({ href, label: itemLabel, icon: Icon, exact }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
              isActive(href, exact)
                ? "bg-card text-white"
                : "text-muted hover:bg-card hover:text-white"
            )}
          >
            <Icon className="h-4 w-4" />
            {itemLabel}
          </Link>
        ))}
      </nav>
      <p className="mt-auto pt-8 text-[10px] text-muted/60">AI Drift Doctor v1.0</p>
    </aside>
  );
}
