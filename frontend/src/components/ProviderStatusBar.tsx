"use client";

import React, { useEffect, useState } from "react";
import { Activity, AlertTriangle } from "lucide-react";

interface ProviderStatus {
  status: boolean;
  last_checked: number;
}

interface HealthResponse {
  providers: {
    gemini?: ProviderStatus;
    groq?: ProviderStatus;
    cerebras?: ProviderStatus;
  };
}

export default function ProviderStatusBar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const rawBaseUrl = process.env.NEXT_PUBLIC_HF_API_URL || "http://localhost:8000";
        const baseUrl = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl;
        const res = await fetch(`${baseUrl}/health`);
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch (error) {
        console.error("Failed to fetch provider health:", error);
      }
    };

    // Fetch immediately on mount
    fetchHealth();

    // Refresh every 60 seconds
    const interval = setInterval(fetchHealth, 60000);
    return () => clearInterval(interval);
  }, []);

  if (!health) {
    return (
      <div className="flex items-center space-x-2 text-zinc-500 text-xs font-mono animate-pulse">
        <Activity size={14} />
        <span>Initializing Forensics Network...</span>
      </div>
    );
  }

  const providers = health.providers;
  const isGeminiHealthy = providers.gemini?.status ?? false;
  const isGroqHealthy = providers.groq?.status ?? false;
  const isCerebrasHealthy = providers.cerebras?.status ?? false;

  const anyDown = !isGeminiHealthy || !isGroqHealthy || !isCerebrasHealthy;

  const StatusPill = ({
    label,
    isHealthy,
  }: {
    label: string;
    isHealthy: boolean;
  }) => (
    <div
      className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full border text-xs font-mono ${
        isHealthy
          ? "bg-emerald-950/30 border-emerald-900/50 text-emerald-400"
          : "bg-red-950/30 border-red-900/50 text-red-400"
      }`}
    >
      <div
        className={`w-1.5 h-1.5 rounded-full ${isHealthy ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"}`}
      />
      <span>{label}</span>
    </div>
  );

  return (
    <div className="flex items-center space-x-4">
      <div className="flex items-center space-x-2">
        <StatusPill label="Gemini" isHealthy={isGeminiHealthy} />
        <StatusPill label="Groq Scout" isHealthy={isGroqHealthy} />
        <StatusPill label="Cerebras" isHealthy={isCerebrasHealthy} />
      </div>

      {anyDown && (
        <div className="flex items-center space-x-2 text-xs font-medium text-amber-500 bg-amber-950/30 px-3 py-1 rounded-full border border-amber-900/50">
          <AlertTriangle size={14} />
          <span>
            Running in degraded mode — results may have lower confidence
          </span>
        </div>
      )}
    </div>
  );
}
