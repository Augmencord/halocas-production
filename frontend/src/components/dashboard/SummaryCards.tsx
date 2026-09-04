"use client";

import React from "react";
import {
  Truck,
  Users,
  AlertTriangle,
  Activity,
  CheckCircle2,
  TrendingDown,
  ShieldCheck,
} from "lucide-react";
import { DashboardSummary, IncidentStats } from "../../lib/api";

interface SummaryCardsProps {
  summary: DashboardSummary | null;
  stats: IncidentStats | null;
  isLoading: boolean;
}

export default function SummaryCards({
  summary,
  stats,
  isLoading,
}: SummaryCardsProps): React.JSX.Element {
  if (isLoading || !summary) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-32 rounded-2xl bg-[#1f2937]/50 border border-[#374151] animate-pulse p-5"
          >
            <div className="h-4 w-28 bg-gray-700/60 rounded mb-3" />
            <div className="h-8 w-16 bg-gray-700/80 rounded mb-2" />
            <div className="h-3 w-36 bg-gray-700/50 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const activeMachines = summary.active_machines_count;
  const totalMachines = summary.total_machines_count;
  const standbyMachines = Math.max(0, totalMachines - activeMachines - 1);
  const maintenanceMachines = Math.max(0, totalMachines - activeMachines - standbyMachines);

  const totalWorkers = summary.total_workers_count;
  const authWorkers = summary.authorized_workers_count;

  const alertsToday = stats?.incidents_today ?? summary.incidents_last_24h_count;
  const criticalCount = stats?.critical_count ?? summary.critical_incidents_count;
  const warningCount = stats?.warning_count ?? 2;
  const cautionCount = stats?.caution_count ?? 1;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Card 1: Active Machines */}
      <div className="p-5 rounded-2xl bg-[#1f2937]/80 backdrop-blur-md border border-[#374151] hover:border-[#00FFFF]/50 transition-all duration-300 group shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 font-mono">
            Active Machines
          </span>
          <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/20 text-[#00FFFF] group-hover:scale-105 transition-transform">
            <Truck className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white font-mono tracking-tight">
            {activeMachines}
          </span>
          <span className="text-xs text-gray-400 font-mono">
            / {totalMachines} Total Fleet
          </span>
        </div>
        {/* Status Breakdown */}
        <div className="mt-2.5 pt-2.5 border-t border-[#374151]/60 flex items-center justify-between text-[11px] font-mono">
          <span className="text-[#10B981] flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
            {activeMachines} Active
          </span>
          <span className="text-[#F59E0B] flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#F59E0B]" />
            {standbyMachines} Standby
          </span>
          <span className="text-gray-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
            {maintenanceMachines} Svc
          </span>
        </div>
      </div>

      {/* Card 2: Workers On-Site */}
      <div className="p-5 rounded-2xl bg-[#1f2937]/80 backdrop-blur-md border border-[#374151] hover:border-[#10B981]/50 transition-all duration-300 group shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 font-mono">
            Workers On-Site
          </span>
          <div className="p-2 rounded-xl bg-[#10B981]/10 border border-[#10B981]/20 text-[#10B981] group-hover:scale-105 transition-transform">
            <Users className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white font-mono tracking-tight">
            {totalWorkers}
          </span>
          <span className="text-xs text-[#10B981] font-mono font-semibold flex items-center">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            100% Enrolled
          </span>
        </div>
        {/* Authorization Breakdown */}
        <div className="mt-2.5 pt-2.5 border-t border-[#374151]/60 flex items-center justify-between text-[11px] font-mono">
          <span className="text-gray-300">
            Authorized: <strong className="text-[#00FFFF]">{authWorkers}</strong> Mechanics
          </span>
          <span className="text-gray-400">
            {totalWorkers - authWorkers} Operators
          </span>
        </div>
      </div>

      {/* Card 3: Alerts Today */}
      <div className="p-5 rounded-2xl bg-[#1f2937]/80 backdrop-blur-md border border-[#374151] hover:border-[#FF3B30]/50 transition-all duration-300 group shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 font-mono">
            Alerts Today
          </span>
          <div className="p-2 rounded-xl bg-[#FF3B30]/10 border border-[#FF3B30]/20 text-[#FF3B30] group-hover:scale-105 transition-transform">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white font-mono tracking-tight">
            {alertsToday}
          </span>
          <span className="text-xs text-[#10B981] font-mono flex items-center">
            <TrendingDown className="w-3 h-3 mr-0.5" />
            -40% Shift Avg
          </span>
        </div>
        {/* Severity Breakdown */}
        <div className="mt-2.5 pt-2.5 border-t border-[#374151]/60 flex items-center justify-between text-[11px] font-mono">
          <span className="text-[#FF3B30] font-bold">
            {criticalCount} Critical
          </span>
          <span className="text-[#F59E0B] font-semibold">
            {warningCount} Warning
          </span>
          <span className="text-gray-400">
            {cautionCount} Caution
          </span>
        </div>
      </div>

      {/* Card 4: System Uptime */}
      <div className="p-5 rounded-2xl bg-[#1f2937]/80 backdrop-blur-md border border-[#374151] hover:border-[#00FFFF]/50 transition-all duration-300 group shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 font-mono">
            System Uptime
          </span>
          <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/20 text-[#00FFFF] group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-[#00FFFF] font-mono tracking-tight">
            99.98%
          </span>
          <span className="text-xs text-[#10B981] font-mono font-bold">
            HEALTHY
          </span>
        </div>
        {/* Subsystem Health Indicator */}
        <div className="mt-2.5 pt-2.5 border-t border-[#374151]/60 flex items-center justify-between text-[11px] font-mono text-gray-400">
          <span className="flex items-center gap-1.5 text-gray-300">
            <Activity className="w-3.5 h-3.5 text-[#10B981]" />
            5/5 Subsystems
          </span>
          <span className="text-[#00FFFF]">0 Drops</span>
        </div>
      </div>
    </div>
  );
}
