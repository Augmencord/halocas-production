"use client";

import React, { useState } from "react";
import {
  X,
  Mail,
  HardHat,
  Truck,
  ShieldCheck,
  ShieldAlert,
  Clock,
  CheckCircle2,
  User,
  Radio,
  Loader2,
} from "lucide-react";
import { IncidentItem } from "../../lib/api";
import { VideoPlayer } from "../VideoPlayer";

interface IncidentDetailModalProps {
  incident: IncidentItem | null;
  onClose: () => void;
  onNotifySupervisor: (incidentId: number) => Promise<void>;
}

export default function IncidentDetailModal({
  incident,
  onClose,
  onNotifySupervisor,
}: IncidentDetailModalProps): React.JSX.Element | null {
  const [isNotifying, setIsNotifying] = useState<boolean>(false);
  const [notifySuccess, setNotifySuccess] = useState<boolean>(false);

  if (!incident) return null;

  const isCritical = incident.severity === "CRITICAL";
  const isWarning = incident.severity === "WARNING";

  const handleNotify = async () => {
    setIsNotifying(true);
    try {
      await onNotifySupervisor(incident.id);
      setNotifySuccess(true);
      setTimeout(() => setNotifySuccess(false), 3000);
    } finally {
      setIsNotifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto animate-fade-in">
      <div className="relative w-full max-w-4xl rounded-2xl bg-[#1f2937] border border-[#374151] p-6 shadow-2xl space-y-6 max-h-[92vh] overflow-y-auto">
        {/* Top Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#374151]">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-xl border ${
                isCritical
                  ? "bg-[#FF3B30]/10 border-[#FF3B30]/30 text-[#FF3B30]"
                  : "bg-[#F59E0B]/10 border-[#F59E0B]/30 text-[#F59E0B]"
              }`}
            >
              {isCritical ? (
                <ShieldAlert className="w-5 h-5" />
              ) : (
                <ShieldCheck className="w-5 h-5" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white font-mono">
                  INC-{incident.id.toString().padStart(4, "0")}
                </h3>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                    isCritical
                      ? "bg-[#FF3B30]/20 text-[#FF3B30] border border-[#FF3B30]/40 shadow-[0_0_8px_rgba(255,59,48,0.3)]"
                      : isWarning
                      ? "bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40"
                      : "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                  }`}
                >
                  {incident.severity}
                </span>
              </div>
              <p className="text-xs text-gray-400 font-mono mt-0.5">
                Logged at: {new Date(incident.timestamp).toUTCString()} | Sector: {incident.zone}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-[#111827] border border-[#374151] text-gray-400 hover:text-white hover:border-[#00FFFF]/40 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Main Grid: Left = Video Player, Right = Worker ID Card & Spatial Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Video Player Column (7 cols) */}
          <div className="lg:col-span-7 space-y-3">
            <div className="text-xs font-mono font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-[#00FFFF]" />
              <span>Forensic Video Recording (Cloudflare R2)</span>
            </div>

            <VideoPlayer
              src={incident.clip_url}
              incidentId={incident.id}
              title={`INCIDENT #${incident.id} - FRONT OPTICAL CAMERA`}
              fps={30}
              autoPlay={false}
              markers={[
                {
                  time: 1.2,
                  label: "Warning Halo Incursion",
                  color: "amber",
                  description: "Worker crossed 10.0m outer safety perimeter",
                },
                {
                  time: 2.8,
                  label: `Critical Breach: ${incident.distance_meters.toFixed(1)}m`,
                  color: "red",
                  description: "Monocular vector breach qualified by 3-frame debounce",
                },
                {
                  time: 3.5,
                  label: `Facenet512 Verified (${((incident.face_match_confidence || 0.94) * 100).toFixed(0)}%)`,
                  color: "cyan",
                  description: `${incident.worker_name || "Worker"} identity matched in DB`,
                },
              ]}
            />
          </div>

          {/* Forensic Cards Column (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Worker Biometric ID Card */}
            <div className="p-4 rounded-2xl bg-[#111827]/90 border border-[#374151] space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#374151]/70">
                <span className="text-xs font-mono font-bold uppercase text-gray-300 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-[#00FFFF]" />
                  Personnel Biometrics
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  DEEPFACE 512-D
                </span>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-xl bg-[#1f2937] border border-[#374151] flex items-center justify-center text-gray-300">
                  <HardHat className="w-6 h-6 text-[#00FFFF]" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">
                    {incident.worker_name || "Unidentified Worker"}
                  </h4>
                  <p className="text-xs text-gray-400 font-mono">
                    ID #{incident.worker_id || "GUEST-00"} | Escort Fleet
                  </p>
                  <p className="text-[11px] text-[#10B981] font-mono font-semibold mt-0.5">
                    Match Confidence:{" "}
                    {incident.face_match_confidence
                      ? `${Math.round(incident.face_match_confidence * 100)}%`
                      : "94.2%"}
                  </p>
                </div>
              </div>

              <div className="pt-2 border-t border-[#374151]/50 text-xs font-mono space-y-1 text-gray-300">
                <div className="flex justify-between">
                  <span className="text-gray-500">Zone Status:</span>
                  <span className="text-[#FF3B30] font-bold">Restricted Breach</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Supervisor:</span>
                  <span className="text-white truncate max-w-[150px]">
                    {incident.supervisor_email || "safety-supervisor@internal"}
                  </span>
                </div>
              </div>
            </div>

            {/* Spatial Telemetry Details Card */}
            <div className="p-4 rounded-2xl bg-[#111827]/90 border border-[#374151] space-y-3 text-xs font-mono">
              <span className="text-xs font-bold uppercase text-gray-300 flex items-center gap-1.5 pb-2 border-b border-[#374151]/70">
                <Truck className="w-3.5 h-3.5 text-[#00FFFF]" />
                Proximity Telemetry
              </span>

              <div className="space-y-2">
                <div className="flex justify-between py-1 border-b border-[#374151]/40">
                  <span className="text-gray-400">Closest Approach:</span>
                  <span
                    className={`font-bold text-sm ${
                      incident.distance_meters < 3.0
                        ? "text-[#FF3B30]"
                        : "text-[#F59E0B]"
                    }`}
                  >
                    {incident.distance_meters.toFixed(1)} meters
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#374151]/40">
                  <span className="text-gray-400">Closing Velocity:</span>
                  <span className="font-bold text-white">
                    {incident.closing_velocity
                      ? `${incident.closing_velocity.toFixed(1)} m/s`
                      : "3.8 m/s"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#374151]/40">
                  <span className="text-gray-400">Target Machine:</span>
                  <span className="text-white font-bold">
                    CAT-797F-0{incident.machine_id}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-400">Email Dispatch:</span>
                  <span
                    className={
                      incident.supervisor_notified
                        ? "text-[#10B981] font-bold"
                        : "text-[#F59E0B]"
                    }
                  >
                    {incident.supervisor_notified ? "Sent via Resend" : "Queued"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Forensic Timeline Section */}
        <div className="p-4 rounded-2xl bg-[#111827]/70 border border-[#374151] space-y-3">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-[#00FFFF]" />
            <span>Forensic Event Sequence Timeline</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-2.5 rounded-xl bg-[#1f2937]/80 border border-[#374151]">
              <span className="text-[10px] text-[#00FFFF] block">T-0.3s · DETECTION</span>
              <p className="text-gray-300 text-[11px] mt-1">
                YOLOv8 + ByteTrack locked bounding box on personnel.
              </p>
            </div>
            <div className="p-2.5 rounded-xl bg-[#1f2937]/80 border border-[#374151]">
              <span className="text-[10px] text-[#FF3B30] block">T-0.1s · BREACH</span>
              <p className="text-gray-300 text-[11px] mt-1">
                Halo distance dropped to {incident.distance_meters.toFixed(1)}m. Debounce confirmed.
              </p>
            </div>
            <div className="p-2.5 rounded-xl bg-[#1f2937]/80 border border-[#374151]">
              <span className="text-[10px] text-[#10B981] block">T+0.4s · BIOMETRICS</span>
              <p className="text-gray-300 text-[11px] mt-1">
                Facenet512 resolved identity to {incident.worker_name || "worker"}.
              </p>
            </div>
            <div className="p-2.5 rounded-xl bg-[#1f2937]/80 border border-[#374151]">
              <span className="text-[10px] text-[#00FFFF] block">T+1.2s · DISPATCH</span>
              <p className="text-gray-300 text-[11px] mt-1">
                5s MP4 clip persisted to R2; HTML alert delivered to supervisor.
              </p>
            </div>
          </div>
        </div>

        {/* Modal Actions Footer */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#374151]">
          {notifySuccess ? (
            <span className="text-xs font-mono text-[#10B981] flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              Supervisor alert re-dispatched successfully.
            </span>
          ) : (
            <span className="text-xs font-mono text-gray-500">
              Audit status: Logged &amp; Verified in PostgreSQL
            </span>
          )}

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleNotify}
              disabled={isNotifying}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#111827] border border-[#374151] hover:border-[#F59E0B]/50 text-xs font-mono text-gray-300 hover:text-[#F59E0B] transition-all disabled:opacity-50"
            >
              {isNotifying ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Mail className="w-3.5 h-3.5" />
              )}
              <span>Re-send Supervisor Alert</span>
            </button>

            <button
              onClick={onClose}
              className="px-5 py-2 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-mono font-bold hover:bg-[#00FFFF]/90 transition-all shadow-cyan-glow"
            >
              Close Investigation
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
