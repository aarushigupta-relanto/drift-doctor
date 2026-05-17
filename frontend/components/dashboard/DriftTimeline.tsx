"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { CardStatic } from "@/components/ui/Card";

const MOCK = [
  { t: "T-6h", conf: 0.88, psi: 0.12, sev: 1 },
  { t: "T-5h", conf: 0.85, psi: 0.15, sev: 1 },
  { t: "T-4h", conf: 0.82, psi: 0.18, sev: 2 },
  { t: "T-3h", conf: 0.74, psi: 0.28, sev: 2 },
  { t: "T-2h", conf: 0.65, psi: 0.35, sev: 3 },
  { t: "T-1h", conf: 0.53, psi: 0.42, sev: 3 },
  { t: "Now", conf: 0.5, psi: 0.48, sev: 3 },
];

export function DriftTimeline() {
  return (
    <CardStatic>
      <h3 className="mb-4 text-sm font-medium text-white">Drift timeline</h3>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={MOCK}>
            <CartesianGrid stroke="#222" strokeDasharray="3 3" />
            <XAxis dataKey="t" stroke="#666" fontSize={11} />
            <YAxis stroke="#666" fontSize={11} domain={[0, 1]} />
            <Tooltip
              contentStyle={{
                background: "#111",
                border: "1px solid #222",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="conf"
              stroke="#fff"
              strokeWidth={1.5}
              dot={false}
              name="Confidence"
            />
            <Line
              type="monotone"
              dataKey="psi"
              stroke="#8B7B4A"
              strokeWidth={1.5}
              dot={false}
              name="PSI"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-muted">
        Confidence trend, PSI proxy, and severity index over the monitoring window.
      </p>
    </CardStatic>
  );
}
