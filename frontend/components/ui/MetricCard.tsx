"use client";

import { METRIC_GLOSSARY } from "@/lib/glossary";
import { cn } from "@/lib/utils";
import { InfoTooltip } from "./Tooltip";

export function MetricCard({
  label,
  value,
  sub,
  alert,
  glossaryKey,
  trend,
}: {
  label: string;
  value: string | number;
  sub?: string;
  alert?: "high" | "medium" | "low" | "none";
  glossaryKey?: string;
  trend?: "up" | "down" | "flat";
}) {
  const g = glossaryKey ? METRIC_GLOSSARY[glossaryKey] : null;
  const tooltip = g ? (
    <>
      <p className="text-white">{g.definition}</p>
      <p>
        <span className="text-white/70">Normal: </span>
        {g.normalRange}
      </p>
      <p>{g.whyItMatters}</p>
    </>
  ) : null;

  const alertClass =
    alert === "high"
      ? "text-alert"
      : alert === "medium"
        ? "text-warning"
        : alert === "low"
          ? "text-success"
          : "text-white";

  return (
    <div className="rounded-xl border border-border bg-card px-4 py-3">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-xs uppercase tracking-wider text-muted">{label}</span>
        {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <p className={cn("text-2xl font-medium tracking-tight", alertClass)}>
        {value}
        {trend === "down" && <span className="ml-1 text-sm text-alert">↓</span>}
        {trend === "up" && <span className="ml-1 text-sm text-warning">↑</span>}
      </p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}
