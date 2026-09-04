"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Search,
  Download,
  Play,
  HardHat,
} from "lucide-react";

interface IncidentRecord {
  id: string;
  timestamp: string;
  workerName: string;
  workerRole: string;
  machineId: string;
  machineType: string;
  distance: number;
  severity: "CRITICAL" | "WARNING";
  closingVelocity: number;
  supervisorNotified: boolean;
  supervisorEmail: string;
  faceConfidence: number;
  clipUrl: string;
}

const incidentsData: IncidentRecord[] = [
  {
    id: "INC-2026-0042",
    timestamp: "2026-09-04 14:28:11 UTC",
    workerName: "Marcus Vance",
    workerRole: "Haul Truck Escort",
    machineId: "CAT-797F-01",
    machineType: "Ultra-Class Haul Truck",
    distance: 2.3,
    severity: "CRITICAL",
    closingVelocity: 3.8,
    supervisorNotified: true,
    supervisorEmail: "safety-supervisor@halocas-mine.internal",
    faceConfidence: 0.94,
    clipUrl: "/clips/mock-clip-0042.mp4",
  },
  {
    id: "INC-2026-0041",
    timestamp: "2026-09-04 14:12:05 UTC",
    workerName: "Elena Rostova",
    workerRole: "Field Mechanic",
    machineId: "KOMATSU-930E-03",
    machineType: "Haul Truck",
    distance: 6.8,
    severity: "WARNING",
    closingVelocity: 1.4,
    supervisorNotified: false,
    supervisorEmail: "field-lead@halocas-mine.internal",
    faceConfidence: 0.88,
    clipUrl: "/clips/mock-clip-0041.mp4",
  },
  {
    id: "INC-2026-0040",
    timestamp: "2026-09-04 13:05:49 UTC",
    workerName: "David Chen",
    workerRole: "Blasting Technician",
    machineId: "HITACHI-EX8000-02",
    machineType: "Hydraulic Shovel",
    distance: 7.2,
    severity: "WARNING",
    closingVelocity: 0.9,
    supervisorNotified: false,
    supervisorEmail: "safety-supervisor@halocas-mine.internal",
    faceConfidence: 0.91,
    clipUrl: "/clips/mock-clip-0040.mp4",
  },
  {
    id: "INC-2026-0039",
    timestamp: "2026-09-04 11:44:20 UTC",
    workerName: "Marcus Vance",
    workerRole: "Haul Truck Escort",
    machineId: "CAT-797F-01",
    machineType: "Ultra-Class Haul Truck",
    distance: 2.8,
    severity: "CRITICAL",
    closingVelocity: 2.7,
    supervisorNotified: true,
    supervisorEmail: "safety-supervisor@halocas-mine.internal",
    faceConfidence: 0.96,
    clipUrl: "/clips/mock-clip-0039.mp4",
  },
];

export default function IncidentsPage(): React.JSX.Element {
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedIncident, setSelectedIncident] = useState<IncidentRecord | null>(
    incidentsData[0]
  );

  const filteredIncidents = incidentsData.filter((inc) => {
    const matchesSeverity =
      filterSeverity === "ALL" || inc.severity === filterSeverity;
    const matchesSearch =
      inc.workerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.machineId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSeverity && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Search and Filters Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by worker, machine, or incident ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF]"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {["ALL", "CRITICAL", "WARNING"].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all ${
                filterSeverity === sev
                  ? "bg-[#00FFFF] text-[#111827] shadow-cyan-glow"
                  : "bg-[#111827] text-gray-400 hover:text-white border border-[#374151]"
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Incident Table & Detail Replay Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Incident Table */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#FF3B30]" />
              Proximity Breach Log ({filteredIncidents.length})
            </h3>
            <span className="text-xs text-gray-400 font-mono">
              Auto-archived to Cloudflare R2
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#374151] text-gray-400 font-mono uppercase text-[10px]">
                  <th className="pb-3 font-semibold">Incident</th>
                  <th className="pb-3 font-semibold">Worker</th>
                  <th className="pb-3 font-semibold">Machine</th>
                  <th className="pb-3 font-semibold">Distance</th>
                  <th className="pb-3 font-semibold">Severity</th>
                  <th className="pb-3 font-semibold text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#374151]/60">
                {filteredIncidents.map((incident) => {
                  const isSelected = selectedIncident?.id === incident.id;
                  return (
                    <tr
                      key={incident.id}
                      onClick={() => setSelectedIncident(incident)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-[#00FFFF]/10 border-l-2 border-[#00FFFF]"
                          : "hover:bg-[#111827]/40"
                      }`}
                    >
                      <td className="py-3 px-2 font-mono text-gray-300 font-medium">
                        {incident.id}
                        <div className="text-[10px] text-gray-400">
                          {incident.timestamp.substring(11, 19)}
                        </div>
                      </td>
                      <td className="py-3 px-2 text-white font-medium">
                        <div className="flex items-center gap-1.5">
                          <HardHat className="w-3.5 h-3.5 text-gray-400" />
                          <span>{incident.workerName}</span>
                        </div>
                        <div className="text-[10px] text-gray-400">
                          {incident.workerRole}
                        </div>
                      </td>
                      <td className="py-3 px-2 text-gray-300 font-mono">
                        {incident.machineId}
                      </td>
                      <td className="py-3 px-2 font-mono font-bold text-white">
                        {incident.distance.toFixed(1)} m
                      </td>
                      <td className="py-3 px-2">
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
                      <td className="py-3 px-2 text-right">
                        <span className="text-[#00FFFF] hover:underline font-mono text-[11px]">
                          Inspect &rarr;
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Incident Replay Inspector */}
        <div className="space-y-4">
          {selectedIncident ? (
            <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white font-mono">
                  {selectedIncident.id}
                </h3>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                    selectedIncident.severity === "CRITICAL"
                      ? "bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30"
                      : "bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30"
                  }`}
                >
                  {selectedIncident.severity}
                </span>
              </div>

              {/* Video Replay Box */}
              <div className="relative aspect-video w-full rounded-xl bg-[#0B0F17] border border-[#374151] flex items-center justify-center overflow-hidden">
                <div className="absolute inset-0 flex flex-col justify-between p-3 pointer-events-none font-mono text-[10px] text-gray-400">
                  <div className="flex justify-between">
                    <span>R2 ARCHIVE CLIP (5s)</span>
                    <span className="text-[#00FFFF]">ISO-8601 OVERLAY</span>
                  </div>
                  <div className="text-center text-white text-xs font-bold">
                    DIST: {selectedIncident.distance}m | CLOSING: {selectedIncident.closingVelocity}m/s
                  </div>
                </div>
                <div className="p-3 rounded-full bg-[#111827]/90 border border-[#00FFFF]/40 text-[#00FFFF] shadow-cyan-glow cursor-pointer hover:scale-110 transition-transform">
                  <Play className="w-6 h-6 ml-0.5" />
                </div>
              </div>

              {/* Forensic Details */}
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1.5 border-b border-[#374151]/60">
                  <span className="text-gray-400">Timestamp</span>
                  <span className="font-mono text-gray-200">
                    {selectedIncident.timestamp}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#374151]/60">
                  <span className="text-gray-400">Worker Biometric Match</span>
                  <span className="font-mono text-[#10B981] font-bold">
                    Facenet512 ({Math.round(selectedIncident.faceConfidence * 100)}%)
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#374151]/60">
                  <span className="text-gray-400">Target Machine</span>
                  <span className="font-mono text-white">
                    {selectedIncident.machineId}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#374151]/60">
                  <span className="text-gray-400">Closing Velocity</span>
                  <span className="font-mono text-[#FF3B30] font-bold">
                    {selectedIncident.closingVelocity} m/s
                  </span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-gray-400">Supervisor Email</span>
                  <span className="font-mono text-xs text-gray-300 truncate max-w-[170px]">
                    {selectedIncident.supervisorEmail}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="pt-2">
                <button className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/40 text-xs font-semibold text-gray-200 hover:text-white transition-all">
                  <Download className="w-3.5 h-3.5 text-[#00FFFF]" />
                  <span>Download Incident Replay (.mp4)</span>
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
