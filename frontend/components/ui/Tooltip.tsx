"use client";

import { Info } from "lucide-react";
import { DRIFT_TYPE_GLOSSARY } from "@/lib/glossary";
import { cn } from "@/lib/utils";

export function InfoTooltip({
  content,
  className,
}: {
  content: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={cn("group relative inline-flex align-middle", className)}>
      <Info className="h-3.5 w-3.5 text-muted cursor-help" />
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-lg border border-border bg-[#1a1a1a] p-3 text-xs leading-relaxed text-muted opacity-0 shadow-soft transition-opacity group-hover:opacity-100"
      >
        {content}
      </span>
    </span>
  );
}

export function DriftChip({ type }: { type: string }) {
  const info = DRIFT_TYPE_GLOSSARY[type];
  const body = info ? (
    <>
      <p className="font-medium text-white">{info.label}</p>
      <p>{info.meaning}</p>
      <p className="mb-1 mt-2 text-[10px] uppercase tracking-wider text-white/80">
        Triggered by
      </p>
      <ul className="list-disc pl-3">
        {info.triggeredBy.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <p className="mb-1 mt-2 text-[10px] uppercase tracking-wider text-white/80">
        Operational impact
      </p>
      <ul className="list-disc pl-3">
        {info.impact.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </>
  ) : (
    <p>Drift signal: {type}</p>
  );

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-[#1a1a1a] px-3 py-1 text-xs text-white/90">
      {type}
      <InfoTooltip content={<div className="space-y-1 text-left">{body}</div>} />
    </span>
  );
}

