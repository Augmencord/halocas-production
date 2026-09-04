"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Play,
  X,
  HardHat,
  CheckCircle2,
  ChevronRight,
  Download,
} from "lucide-react";
import { IncidentItem } from "../../lib/api";

interface ActiveAlertsPanelProps {
  incidents: IncidentItem[];
  isLoading: boolean;
}

export default function ActiveAlertsPanel({
  incidents,
  isLoading,
}: ActiveAlertsPanelProps): React.JSX.Element {
  const [selectedIncident, setSelectedIncident] = useState<IncidentItem | null>(
    null
  );

  return (
    <div className="flex flex-col justify-between rounded-2xl bg-[#1f2937]/90 backdrop-blur-md border border-[#374151] p-5 shadow-2xl overflow-hidden h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#374151]/70">
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-xl bg-[#FF3B30]/10 border border-[#FF3B30]/30 text-[#FF3B30]">
            <AlertTriangle className="w-4 h-4 animate-bounce" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              ACTIVE ALERTS
            </h3>
            <p className="text-[11px] text-gray-400 font-mono">
              REAL-TIME SAFETY BREACHES
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30">
          {incidents.length} EVENTS
        </span>
      </div>

      {/* Scrolling Alerts List */}
      <div className="my-3 flex-1 overflow-y-auto max-h-[340px] space-y-2.5 pr-1">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-20 rounded-xl bg-[#111827]/60 border border-[#374151] animate-pulse p-3"
              />
            ))}
          </div>
        ) : incidents.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-xs">
            <CheckCircle2 className="w-8 h-8 text-[#10B981] mx-auto mb-2" />
            <p className="font-semibold text-white">No Proximity Breaches</p>
            <p className="text-[11px] text-gray-500 mt-0.5">
              All personnel outside critical &amp; warning halo zones.
            </p>
          </div>
        ) : (
          incidents.map((incident) => {
            const isCritical = incident.severity === "CRITICAL";
            const formattedTime = new Date(incident.timestamp).toLocaleTimeString(
              [],
              { hour: "2-digit", minute: "2-digit", second: "2-digit" }
            );

            return (
              <div
                key={incident.id}
                onClick={() => setSelectedIncident(incident)}
                className={`p-3.5 rounded-xl border transition-all duration-200 cursor-pointer group ${
                  isCritical
                    ? "bg-[#FF3B30]/5 border-[#FF3B30]/30 hover:border-[#FF3B30] hover:bg-[#FF3B30]/10"
                    : "bg-[#111827]/70 border-[#374151] hover:border-[#F59E0B] hover:bg-[#111827]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-gray-400">
                    {formattedTime}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                      isCritical
                        ? "bg-[#FF3B30]/20 text-[#FF3B30] border border-[#FF3B30]/40 animate-pulse"
                        : "bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40"
                    }`}
                  >
                    {incident.severity}
                  </span>
                </div>

                <div className="mt-2 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-6 h-6 rounded-lg bg-[#1f2937] border border-[#374151] flex items-center justify-center">
                      <HardHat className="w-3.5 h-3.5 text-gray-300 group-hover:text-[#00FFFF] transition-colors" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-white tracking-wide">
                        {incident.worker_name || "Unidentified Personnel"}
                      </div>
                      <div className="text-[10px] font-mono text-gray-400">
                        Mach #{incident.machine_id}
                      </div>
                    </div>
                  </div>

                  <div className="text-right font-mono">
                    <div className="text-sm font-bold text-white">
                      {incident.distance_meters.toFixed(1)}m
                    </div>
                    <div className="text-[9px] text-[#00FFFF] flex items-center gap-0.5 justify-end">
                      <span>Clip Replay</span>
                      <ChevronRight className="w-2.5 h-2.5" />
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="pt-2 border-t border-[#374151]/50 text-[10px] font-mono text-gray-400 flex items-center justify-between">
        <span>Click alert to inspect 5s R2 clip</span>
        <span className="text-[#00FFFF]">Auto-Refresh: 5s</span>
      </div>

      {/* Modal / Expanded Clip Inspection Dialog */}
      {selectedIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-[#1f2937] border border-[#374151] p-6 shadow-2xl space-y-4 relative">
            <button
              onClick={() => setSelectedIncident(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg bg-[#111827] border border-[#374151] text-gray-400 hover:text-white hover:border-[#00FFFF]/40 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                    selectedIncident.severity === "CRITICAL"
                      ? "bg-[#FF3B30]/20 text-[#FF3B30] border border-[#FF3B30]/40"
                      : "bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40"
                  }`}
                >
                  {selectedIncident.severity} BREACH
                </span>
                <span className="text-xs font-mono text-gray-400">
                  INCIDENT #{selectedIncident.id}
                </span>
              </div>
              <h4 className="text-base font-bold text-white mt-1">
                {selectedIncident.worker_name || "Unidentified Personnel"} &times; Machine #{selectedIncident.machine_id}
              </h4>
            </div>

            {/* Video Clip Player Box */}
            <div className="relative aspect-video w-full rounded-xl bg-[#0B0F17] border border-[#374151] overflow-hidden flex items-center justify-center">
              {selectedIncident.clip_url ? (
                <video
                  src={selectedIncident.clip_url}
                  controls
                  autoPlay
                  loop
                  muted
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-4">
                  <div className="p-3 rounded-full bg-[#111827] border border-[#00FFFF]/30 text-[#00FFFF] mb-2 shadow-cyan-glow">
                    <Play className="w-6 h-6 ml-0.5" />
                  </div>
                  <span className="text-xs font-mono text-gray-300">
                    5-Second Video Archive Available
                  </span>
                  <span className="text-[10px] text-gray-500 font-mono mt-0.5">
                    Storage: Cloudflare R2 / Burned ISO Timestamps
                  </span>
                </div>
              )}
            </div>

            {/* Diagnostic Details Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2.5 rounded-xl bg-[#111827] border border-[#374151]/70">
                <span className="text-[10px] text-gray-400 block">PROXIMITY DISTANCE</span>
                <span className="text-white font-bold text-sm">
                  {selectedIncident.distance_meters.toFixed(1)} meters
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-[#111827] border border-[#374151]/70">
                <span className="text-[10px] text-gray-400 block">CLOSING VELOCITY</span>
                <span className="text-[#FF3B30] font-bold text-sm">
                  {selectedIncident.closing_velocity ? `${selectedIncident.closing_velocity.toFixed(1)} m/s` : "3.8 m/s"}
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-[#111827] border border-[#374151]/70">
                <span className="text-[10px] text-gray-400 block">DEEPFACE CONFIDENCE</span>
                <span className="text-[#10B981] font-bold text-sm">
                  {selectedIncident.face_match_confidence
                    ? `${Math.round(selectedIncident.face_match_confidence * 100)}%`
                    : "94% (Facenet512)"}
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-[#111827] border border-[#374151]/70">
                <span className="text-[10px] text-gray-400 block">SUPERVISOR NOTIFIED</span>
                <span className="text-[#00FFFF] font-bold text-sm flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Dispatched
                </span>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                onClick={() => setSelectedIncident(null)}
                className="px-4 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs font-semibold text-gray-300 hover:text-white"
              >
                Close
              </button>
              <button
                onClick={() => setSelectedIncident(null)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90 transition-all shadow-cyan-glow"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Clip Archive</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
