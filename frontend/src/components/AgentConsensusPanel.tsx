"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lock,
  Split,
  AlertTriangle,
  User,
  CheckCircle2,
  XCircle,
} from "lucide-react";

// Interfaces matching the backend
interface AgentFinding {
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
}

interface AgentReport {
  thinking: string;
  agent: string;
  provider: string;
  findings: AgentFinding[];
  confidence: number;
  preliminary_verdict: string;
  reasoning_summary: string;
}

interface FinalVerdict {
  thinking: string;
  verdict: string;
  confidence: number;
  consensus: "full_agreement" | "partial_agreement" | "conflict";
  agent_a_report: AgentReport;
  agent_b_report: AgentReport;
  arbitrator_reasoning: string;
  key_evidence: string[];
}

interface AgentConsensusPanelProps {
  agentAReport: AgentReport | null;
  agentBReport: AgentReport | null;
  finalVerdict: FinalVerdict | null;
  streamingStage: string;
}

export default function AgentConsensusPanel({
  agentAReport,
  agentBReport,
  finalVerdict,
  streamingStage,
}: AgentConsensusPanelProps) {
  // Helper to format confidence
  const formatConfidence = (conf: number) => `${Math.round(conf * 100)}%`;

  // Skeleton Loader for an Agent Card
  const AgentSkeleton = ({ title }: { title: string }) => (
    <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col space-y-4 animate-pulse">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 bg-zinc-800 rounded-full"></div>
        <div className="h-5 bg-zinc-800 rounded w-1/2"></div>
      </div>
      <div className="h-8 bg-zinc-800 rounded w-1/3"></div>
      <div className="space-y-2">
        <div className="h-4 bg-zinc-800 rounded w-full"></div>
        <div className="h-4 bg-zinc-800 rounded w-5/6"></div>
        <div className="h-4 bg-zinc-800 rounded w-4/6"></div>
      </div>
      <div className="mt-auto h-4 bg-zinc-800 rounded w-1/4"></div>
    </div>
  );

  // Agent Card Component
  const AgentCard = ({
    report,
    title,
    isAgentA,
    delay,
  }: {
    report: AgentReport;
    title: string;
    isAgentA: boolean;
    delay: number;
  }) => {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay }}
        className="flex-1 bg-zinc-900/80 border border-zinc-700/50 rounded-xl p-5 flex flex-col shadow-lg"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div
              className={`p-2 rounded-lg ${isAgentA ? "bg-blue-900/30 text-blue-400" : "bg-purple-900/30 text-purple-400"}`}
            >
              <User size={20} />
            </div>
            <h3 className="text-zinc-100 font-semibold">{title}</h3>
          </div>
          <span className="text-xs text-zinc-500 font-mono bg-zinc-950 px-2 py-1 rounded">
            {report.provider}
          </span>
        </div>

        <div className="flex items-end justify-between mb-6 pb-4 border-b border-zinc-800">
          <div>
            <p className="text-sm text-zinc-400 mb-1">Verdict</p>
            <p className="text-lg font-bold text-zinc-100 capitalize">
              {report.preliminary_verdict.replace("_", " ")}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-zinc-400 mb-1">Confidence</p>
            <p className="text-xl font-mono text-emerald-400">
              {formatConfidence(report.confidence)}
            </p>
          </div>
        </div>

        <div className="flex-1">
          <details className="mb-4 group">
            <summary className="text-xs text-zinc-500 font-mono cursor-pointer hover:text-cyan-400 transition-colors list-none flex items-center">
              <span className="w-2 h-2 rounded-full bg-cyan-500/50 mr-2 group-open:animate-pulse"></span>
              View Internal Monologue
            </summary>
            <div className="mt-2 p-3 bg-zinc-950/50 border border-zinc-800 rounded-lg text-xs font-mono text-zinc-400 max-h-32 overflow-y-auto whitespace-pre-wrap">
              {report.thinking}
            </div>
          </details>
          <p className="text-sm text-zinc-400 mb-3">Top Findings</p>
          <ul className="space-y-3">
            {report.findings.slice(0, 3).map((finding, idx) => {
              const isConflict =
                finding.severity === "critical" || finding.severity === "high";
              return (
                <li key={idx} className="flex items-start space-x-2 text-sm">
                  {isConflict ? (
                    <AlertTriangle
                      className="text-amber-500 shrink-0 mt-0.5"
                      size={16}
                    />
                  ) : (
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 mt-1.5" />
                  )}
                  <span
                    className={`break-words whitespace-pre-wrap ${isConflict ? "text-amber-200" : "text-zinc-300"}`}
                  >
                    {finding.description}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      </motion.div>
    );
  };

  const getConsensusIcon = (consensus: string) => {
    switch (consensus) {
      case "full_agreement":
        return <CheckCircle2 className="text-emerald-500" size={32} />;
      case "partial_agreement":
        return <Split className="text-yellow-500" size={32} />;
      case "conflict":
        return <XCircle className="text-red-500" size={32} />;
      default:
        return <Lock className="text-zinc-500" size={32} />;
    }
  };

  return (
    <div className="w-full space-y-8 mt-8">
      {/* Agents Row */}
      <div className="flex flex-col md:flex-row gap-6 relative">
        {/* Agent A Card */}
        {agentAReport ? (
          <AgentCard
            report={agentAReport}
            title="Compression Analyst"
            isAgentA={true}
            delay={0.1}
          />
        ) : (
          <AgentSkeleton title="Compression Analyst" />
        )}

        {/* Consensus Icon overlay in the middle (only shows if both are present) */}
        {agentAReport && agentBReport && finalVerdict && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.6, type: "spring" }}
            className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-zinc-950 border-4 border-zinc-900 rounded-full items-center justify-center z-10 shadow-2xl"
          >
            {getConsensusIcon(finalVerdict.consensus)}
          </motion.div>
        )}

        {/* Agent B Card */}
        {agentBReport ? (
          <AgentCard
            report={agentBReport}
            title="Geometry Auditor"
            isAgentA={false}
            delay={0.3}
          />
        ) : (
          <AgentSkeleton title="Geometry Auditor" />
        )}
      </div>

      {/* Arbitrator Block */}
      <AnimatePresence>
        {finalVerdict && (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.8 }}
            className="bg-zinc-950 border border-zinc-800 rounded-2xl p-6 md:p-8 shadow-2xl relative overflow-hidden"
          >
            {/* Background Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-1 bg-gradient-to-r from-transparent via-emerald-500 to-transparent opacity-50" />

            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-8 pb-6 border-b border-zinc-800/60">
              <div>
                <h2 className="text-zinc-400 text-sm font-medium tracking-wider uppercase mb-2">
                  Final Binding Verdict
                </h2>
                <div className="flex items-center space-x-4">
                  <span
                    className={`text-4xl md:text-5xl font-black capitalize ${finalVerdict.verdict.includes("manipulated") ? "text-red-500" : "text-emerald-500"}`}
                  >
                    {finalVerdict.verdict.replace("_", " ")}
                  </span>
                </div>
              </div>
              <div className="flex flex-col items-end">
                <span className="text-zinc-400 text-sm mb-2">
                  Arbitrator Confidence
                </span>
                <div className="flex items-center space-x-3">
                  <div className="w-32 h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${finalVerdict.confidence * 100}%` }}
                      transition={{ duration: 1, delay: 1 }}
                      className={`h-full ${finalVerdict.confidence > 0.8 ? "bg-emerald-500" : finalVerdict.confidence > 0.5 ? "bg-yellow-500" : "bg-red-500"}`}
                    />
                  </div>
                  <span className="text-2xl font-mono font-bold text-zinc-100">
                    {formatConfidence(finalVerdict.confidence)}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="md:col-span-2 space-y-4">
                <details className="mb-2 group">
                  <summary className="text-xs text-zinc-500 font-mono cursor-pointer hover:text-cyan-400 transition-colors list-none flex items-center">
                    <span className="w-2 h-2 rounded-full bg-cyan-500/50 mr-2 group-open:animate-pulse"></span>
                    View Arbitrator Monologue
                  </summary>
                  <div className="mt-2 p-4 bg-zinc-950/50 border border-zinc-800 rounded-lg text-xs font-mono text-zinc-400 max-h-40 overflow-y-auto whitespace-pre-wrap">
                    {finalVerdict.thinking}
                  </div>
                </details>
                <h3 className="text-zinc-100 font-semibold flex items-center">
                  <Lock className="mr-2 text-zinc-400" size={18} />
                  Reasoning Chain
                </h3>
                <p className="text-zinc-300 leading-relaxed text-sm md:text-base">
                  {finalVerdict.arbitrator_reasoning}
                </p>
              </div>
              <div className="space-y-4">
                <h3 className="text-zinc-100 font-semibold flex items-center">
                  <AlertTriangle className="mr-2 text-amber-500" size={18} />
                  Key Evidence
                </h3>
                <ul className="space-y-3">
                  {finalVerdict.key_evidence.map((evidence, idx) => (
                    <li
                      key={idx}
                      className="flex items-start text-sm text-zinc-400"
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 mt-1.5 mr-2" />
                      {evidence}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
