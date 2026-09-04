"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  fetchDashboardSummary,
  fetchIncidentStats,
  DashboardSummary,
  IncidentStats,
} from "../lib/api";
import SummaryCards from "../components/dashboard/SummaryCards";
import LiveCameraFeed from "../components/dashboard/LiveCameraFeed";
import ActiveAlertsPanel from "../components/dashboard/ActiveAlertsPanel";
import ProximityRadar from "../components/dashboard/ProximityRadar";
import IncidentChart from "../components/dashboard/IncidentChart";
import { RefreshCw, AlertCircle } from "lucide-react";

export default function DashboardPage(): React.JSX.Element {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [stats, setStats] = useState<IncidentStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const performFetch = useCallback(async () => {
    try {
      const [summaryRes, statsRes] = await Promise.all([
        fetchDashboardSummary(),
        fetchIncidentStats(),
      ]);
      setSummary(summaryRes);
      setStats(statsRes);
      setErrorMsg(null);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to connect to backend telemetry";
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await performFetch();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  useEffect(() => {
    let active = true;

    const runInitial = async () => {
      try {
        const [summaryRes, statsRes] = await Promise.all([
          fetchDashboardSummary(),
          fetchIncidentStats(),
        ]);
        if (active) {
          setSummary(summaryRes);
          setStats(statsRes);
          setErrorMsg(null);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (active) {
          setErrorMsg(
            err instanceof Error
              ? err.message
              : "Failed to connect to backend telemetry"
          );
          setIsLoading(false);
        }
      }
    };

    void runInitial();

    const interval = setInterval(() => {
      if (active) {
        void performFetch();
      }
    }, 10000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [performFetch]);

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner: Site Status & Manual Telemetry Refresh */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-[#1f2937] via-[#1f2937]/95 to-[#111827] border border-[#374151] relative overflow-hidden shadow-xl">
        <div className="absolute top-0 right-0 w-96 h-full bg-gradient-to-l from-[#00FFFF]/5 to-transparent pointer-events-none" />
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
              ● RADAR LINK ONLINE
            </span>
            <span className="text-xs text-gray-400 font-mono">
              PIT SECTOR 04 - NORTH CUT
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Executive Safety &amp; Collision Avoidance</span>
          </h2>
          <p className="text-xs text-gray-400">
            Real-time monocular proximity analysis, DeepFace biometrics, and active incident response.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleManualRefresh}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/40 text-xs font-mono text-gray-300 hover:text-white transition-all shadow-sm"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-[#00FFFF] ${
                isRefreshing ? "animate-spin" : ""
              }`}
            />
            <span>Refresh Stream</span>
          </button>
        </div>
      </div>

      {/* Optional Error Notification Banner */}
      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-[#FF3B30]/10 border border-[#FF3B30]/30 text-xs font-mono text-[#FF3B30] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[#FF3B30]" />
            <span>Backend link status: {errorMsg} (Displaying telemetry fallback)</span>
          </div>
          <button
            onClick={handleManualRefresh}
            className="underline hover:text-white"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* 1. Summary Cards Row (4 cards) */}
      <SummaryCards
        summary={summary}
        stats={stats}
        isLoading={isLoading}
      />

      {/* 2 & 3. Live Camera Feed (2/3 width) and Active Alerts Panel (1/3 width) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        <div className="lg:col-span-2">
          <LiveCameraFeed />
        </div>
        <div className="lg:col-span-1">
          <ActiveAlertsPanel
            incidents={summary?.recent_incidents ?? []}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* 4 & 5. 2D Proximity Radar (Canvas) and Real-Time Statistics Chart (Recharts) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-5">
          <ProximityRadar />
        </div>
        <div className="lg:col-span-7">
          <IncidentChart />
        </div>
      </div>
    </div>
  );
}
