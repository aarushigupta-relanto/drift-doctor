"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { LineChart, MessageSquare, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border px-8 py-6">
        <p className="text-xs uppercase tracking-[0.2em] text-muted">
          AI Reliability Platform
        </p>
      </header>

      <main className="mx-auto flex max-w-5xl flex-col items-center px-6 py-24 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-medium tracking-tight md:text-5xl"
        >
          AI Drift Doctor
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mt-3 text-lg text-muted"
        >
          Autonomous AI Health &amp; Drift Monitoring
        </motion.p>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="mt-6 max-w-xl text-balance text-sm leading-relaxed text-muted"
        >
          Monitor production AI systems, detect drift, diagnose failures, and
          automate retraining decisions.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mt-16 grid w-full gap-6 md:grid-cols-2"
        >
          <MonitorCard
            href="/model"
            icon={<LineChart className="h-8 w-8" />}
            title="Predictive Model Monitoring"
            description="Monitor ML systems for confidence drift, feature instability, PSI changes, and production degradation."
            cta="Launch Model Dashboard"
          />
          <MonitorCard
            href="/chatbot"
            icon={<MessageSquare className="h-8 w-8" />}
            title="Chatbot / RAG Monitoring"
            description="Monitor conversational AI for behavioral drift, retrieval degradation, hallucination risk, and stale knowledge."
            cta="Launch Chatbot Dashboard"
          />
        </motion.div>
      </main>
    </div>
  );
}

function MonitorCard({
  href,
  icon,
  title,
  description,
  cta,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  cta: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-2xl border border-border bg-card p-8 text-left shadow-soft transition hover:border-white/20"
    >
      <motion.div className="mb-6 text-white/80 transition group-hover:text-white">
        {icon}
      </motion.div>
      <h2 className="text-xl font-medium">{title}</h2>
      <p className="mt-3 text-sm leading-relaxed text-muted">{description}</p>
      <span className="mt-8 inline-flex items-center gap-2 text-sm text-white">
        {cta}
        <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
