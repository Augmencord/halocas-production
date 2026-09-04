"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  Users,
  Truck,
  Activity,
  ArrowUpRight,
  TrendingDown,
  CheckCircle2,
  Radio,
  ChevronRight,
  RefreshCw,
  HardHat,
  Eye,
  Sliders,
} from "lucide-react";

interface IncidentPreview {
  id: string;
  time: string;
  workerName: string;
  machineName: string;
  distance: number;
  severity: "CRITICAL" | "WARNING";
  closingVelocity: number;
  authorized: boolean;
}

const recentIncidents: IncidentPreview[] = [
  {
    id: "INC-2026-0042",
    time: "2 mins ago",
    workerName: "Marcus Vance",
    machineName: "CAT-797F-01",
    distance: 2.3,
    severity: "CRITICAL",
    closingVelocity: 3.8,
    authorized: false,
  },
  {
    id: "INC-2026-0041",
    time: "14 mins ago",
    workerName: "Elena Rostova",
    machineName: "KOMATSU-930E-03",
    distance: 6.8,
    severity: "WARNING",
    closingVelocity: 1.4,
    authorized: true,
  },
  {
    id: "INC-2026-0040",
    time: "1 hour ago",
    workerName: "David Chen",
    machineName: "HITACHI-EX8000-02",
    distance: 7.2,
    severity: "WARNING",
    closingVelocity: 0.9,
    authorized: false,
  },
];

export default function DashboardPage(): React.JSX.Element {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 600);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-[#1f2937] via-[#1f2937]/90 to-[#111827] border border-[#374151] relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-full bg-gradient-to-l from-[#00FFFF]/5 to-transparent pointer-events-none" />
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
              ● SITE SHIELD NOMINAL
            </span>
            <span className="text-xs text-gray-400 font-mono">
              PIT SECTOR 04 - NORTH CUT
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            High-Risk Proximity Supervision
          </h2>
          <p className="text-sm text-gray-400">
            Autonomous computer vision and DeepFace biometric safety enforcement
            active on all active mining machinery.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/40 text-xs font-medium text-gray-300 hover:text-white transition-all shadow-sm"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-[#00FFFF] ${
                isRefreshing ? "animate-spin" : ""
              }`}
            />
            <span>Refresh Telemetry</span>
          </button>
          <Link
            href="/monitoring"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#00FFFF] hover:bg-[#00FFFF]/90 text-[#111827] text-xs font-bold transition-all shadow-[0_0_15px_rgba(0,255,255,0.3)] hover:shadow-[0_0_20px_rgba(0,255,255,0.5)]"
          >
            <Radio className="w-4 h-4 text-[#111827]" />
            <span>Launch Live Feeds</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Critical Breaches */}
        <div className="p-5 rounded-2xl bg-[#1f2937]/80 border border-[#374151] hover:border-[#FF3B30]/50 transition-all group relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Critical Breaches (24h)
            </span>
            <div className="p-2 rounded-xl bg-[#FF3B30]/10 border border-[#FF3B30]/20 text-[#FF3B30]">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">1</span>
            <span className="text-xs font-medium text-[#10B981] flex items-center">
              <TrendingDown className="w-3 h-3 mr-0.5" /> -67% vs last shift
            </span>
          </div>
          <p className="mt-1 text-[11px] text-gray-400">
            Debounce threshold: 3 frames (100ms)
          </p>
        </div>

        {/* Card 2: Active Heavy Equipment */}
        <div className="p-5 rounded-2xl bg-[#1f2937]/80 border border-[#374151] hover:border-[#00FFFF]/50 transition-all group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Active Machines
            </span>
            <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/20 text-[#00FFFF]">
              <Truck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">8</span>
            <span className="text-xs font-medium text-gray-400">/ 10 units active</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-400">
            CAT 797F, Komatsu 930E, Hitachi EX8000
          </p>
        </div>

        {/* Card 3: Monitored Workers */}
        <div className="p-5 rounded-2xl bg-[#1f2937]/80 border border-[#374151] hover:border-[#10B981]/50 transition-all group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Enrolled Personnel
            </span>
            <div className="p-2 rounded-xl bg-[#10B981]/10 border border-[#10B981]/20 text-[#10B981]">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">24</span>
            <span className="text-xs font-medium text-[#10B981] flex items-center">
              100% biometrics enrolled
            </span>
          </div>
          <p className="mt-1 text-[11px] text-gray-400">
            Facenet512 512-D cosine indexing
          </p>
        </div>

        {/* Card 4: AI Latency & Pipeline */}
        <div className="p-5 rounded-2xl bg-[#1f2937]/80 border border-[#374151] hover:border-[#00FFFF]/50 transition-all group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Detection Latency
            </span>
            <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/20 text-[#00FFFF]">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#00FFFF] font-mono">14.2</span>
            <span className="text-xs font-medium text-gray-400">ms / frame</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-400">
            ByteTrack locked @ 29.8 FPS
          </p>
        </div>
      </div>

      {/* Main Content Grid: Proximity Radar & Subsystem Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Real-time Proximity Radar & Recent Incidents */}
        <div className="lg:col-span-2 space-y-6">
          {/* Spatial Safety Radar HUD */}
          <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Radio className="w-4 h-4 text-[#00FFFF]" />
                  Spatial Halo Safety Radar
                </h3>
                <p className="text-xs text-gray-400">
                  Concentric proximity monitoring (Critical: 3.0m, Warning: 10.0m, Safe: &gt; 10.0m)
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="flex items-center gap-1.5 text-gray-300">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#FF3B30]" />
                  &lt; 3.0m Critical
                </span>
                <span className="flex items-center gap-1.5 text-gray-300">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
                  &lt; 10.0m Warning
                </span>
                <span className="flex items-center gap-1.5 text-gray-300">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
                  Safe Zone
                </span>
              </div>
            </div>

            {/* Radar Visual Display Container */}
            <div className="relative h-64 w-full rounded-xl bg-[#111827] border border-[#374151] overflow-hidden flex items-center justify-center hud-grid">
              {/* Concentric Halo Rings */}
              <div className="absolute w-52 h-52 rounded-full border border-dashed border-[#10B981]/40 flex items-center justify-center">
                <div className="w-36 h-36 rounded-full border border-dashed border-[#F59E0B]/50 flex items-center justify-center">
                  <div className="w-20 h-20 rounded-full border-2 border-[#FF3B30]/70 bg-[#FF3B30]/10 flex items-center justify-center animate-pulse">
                    <Truck className="w-7 h-7 text-white" />
                  </div>
                </div>
              </div>

              {/* Radar Scanner Sweep Line */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-56 h-0.5 bg-gradient-to-r from-transparent via-[#00FFFF] to-transparent animate-[spin_4s_linear_infinite]" />
              </div>

              {/* Worker Target Overlays */}
              <div className="absolute top-16 left-28 flex items-center gap-1.5 bg-[#1f2937]/90 px-2 py-1 rounded border border-[#10B981]/50 text-[10px] font-mono">
                <HardHat className="w-3.5 h-3.5 text-[#10B981]" />
                <span>M. Vance (12.4m)</span>
              </div>

              <div className="absolute bottom-16 right-28 flex items-center gap-1.5 bg-[#1f2937]/90 px-2 py-1 rounded border border-[#F59E0B]/50 text-[10px] font-mono">
                <HardHat className="w-3.5 h-3.5 text-[#F59E0B]" />
                <span>E. Rostova (6.8m)</span>
              </div>

              {/* Bottom Legend Overlay */}
              <div className="absolute bottom-2 left-3 text-[10px] font-mono text-gray-400">
                SENSOR: CALIBRATED @ 20.0 PX/M | ZERO DRIFT
              </div>
              <div className="absolute bottom-2 right-3 text-[10px] font-mono text-[#00FFFF]">
                CAMERA ID: FRONT_OPTICAL_01
              </div>
            </div>
          </div>

          {/* Recent Incident Table */}
          <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">
                  Recent Proximity Violations
                </h3>
                <p className="text-xs text-gray-400">
                  Automated detections logged with R2 video replay captures
                </p>
              </div>
              <Link
                href="/incidents"
                className="flex items-center gap-1 text-xs font-semibold text-[#00FFFF] hover:underline"
              >
                <span>View Full Log</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#374151] text-gray-400 font-mono uppercase text-[10px]">
                    <th className="pb-3 font-semibold">Incident ID</th>
                    <th className="pb-3 font-semibold">Worker</th>
                    <th className="pb-3 font-semibold">Machine</th>
                    <th className="pb-3 font-semibold">Distance</th>
                    <th className="pb-3 font-semibold">Velocity</th>
                    <th className="pb-3 font-semibold">Severity</th>
                    <th className="pb-3 font-semibold text-right">Replay</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#374151]/60">
                  {recentIncidents.map((incident) => (
                    <tr
                      key={incident.id}
                      className="hover:bg-[#111827]/40 transition-colors"
                    >
                      <td className="py-3 font-mono text-gray-300 font-medium">
                        {incident.id}
                      </td>
                      <td className="py-3 text-white font-medium flex items-center gap-1.5">
                        <HardHat className="w-3.5 h-3.5 text-gray-400" />
                        {incident.workerName}
                      </td>
                      <td className="py-3 text-gray-300 font-mono">
                        {incident.machineName}
                      </td>
                      <td className="py-3 font-mono font-bold text-white">
                        {incident.distance.toFixed(1)} m
                      </td>
                      <td className="py-3 font-mono text-gray-300">
                        {incident.closingVelocity.toFixed(1)} m/s
                      </td>
                      <td className="py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                            incident.severity === "CRITICAL"
                              ? "bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30"
                              : "bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30"
                          }`}
                        >
                          {incident.severity}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <Link
                          href={`/incidents?id=${incident.id}`}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/50 text-gray-300 hover:text-[#00FFFF] transition-all"
                        >
                          <Eye className="w-3 h-3" />
                          <span>Review</span>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Subsystem Health & Operations */}
        <div className="space-y-6">
          {/* Subsystem Health Status Card */}
          <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
              Subsystem Health
            </h3>

            <div className="space-y-3">
              {/* Item 1: YOLOv8 */}
              <div className="p-3 rounded-xl bg-[#111827]/70 border border-[#374151] flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">
                    YOLOv8n + ByteTrack
                  </div>
                  <div className="text-[11px] text-gray-400">
                    Weights: yolov8n.pt (Classes 0, 7)
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  ONLINE
                </span>
              </div>

              {/* Item 2: DeepFace */}
              <div className="p-3 rounded-xl bg-[#111827]/70 border border-[#374151] flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">
                    Facenet512 Biometrics
                  </div>
                  <div className="text-[11px] text-gray-400">
                    Backend: RetinaFace (512-D)
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  ONLINE
                </span>
              </div>

              {/* Item 3: Circular Frame Buffer */}
              <div className="p-3 rounded-xl bg-[#111827]/70 border border-[#374151] flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">
                    Rolling Frame Buffer
                  </div>
                  <div className="text-[11px] text-gray-400">
                    Capacity: 1,800 frames (60 sec)
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  ACTIVE
                </span>
              </div>

              {/* Item 4: Cloudflare R2 */}
              <div className="p-3 rounded-xl bg-[#111827]/70 border border-[#374151] flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">
                    Cloudflare R2 Storage
                  </div>
                  <div className="text-[11px] text-gray-400">
                    Bucket: halocas-clips
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  READY
                </span>
              </div>

              {/* Item 5: Resend Notification */}
              <div className="p-3 rounded-xl bg-[#111827]/70 border border-[#374151] flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">
                    Resend Email Gateway
                  </div>
                  <div className="text-[11px] text-gray-400">
                    Rate Limit: 10/min/supervisor
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  READY
                </span>
              </div>
            </div>
          </div>

          {/* Quick System Controls */}
          <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#00FFFF]" />
              Quick Actions
            </h3>

            <div className="space-y-2">
              <Link
                href="/settings"
                className="flex items-center justify-between p-3 rounded-xl bg-[#111827]/80 border border-[#374151] hover:border-[#00FFFF]/40 text-xs font-medium text-gray-200 hover:text-white transition-all group"
              >
                <span>Calibrate Spatial Distances</span>
                <ArrowUpRight className="w-4 h-4 text-gray-400 group-hover:text-[#00FFFF]" />
              </Link>
              <Link
                href="/workers"
                className="flex items-center justify-between p-3 rounded-xl bg-[#111827]/80 border border-[#374151] hover:border-[#00FFFF]/40 text-xs font-medium text-gray-200 hover:text-white transition-all group"
              >
                <span>Enroll New Personnel Face</span>
                <ArrowUpRight className="w-4 h-4 text-gray-400 group-hover:text-[#00FFFF]" />
              </Link>
              <Link
                href="/monitoring"
                className="flex items-center justify-between p-3 rounded-xl bg-[#111827]/80 border border-[#374151] hover:border-[#00FFFF]/40 text-xs font-medium text-gray-200 hover:text-white transition-all group"
              >
                <span>Switch Camera Multi-Angle</span>
                <ArrowUpRight className="w-4 h-4 text-gray-400 group-hover:text-[#00FFFF]" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
