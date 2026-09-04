"use client";

import React, { useState } from "react";
import {
  Users,
  ShieldCheck,
  Search,
  Camera,
  HardHat,
  CheckCircle2,
  XCircle,
} from "lucide-react";

interface WorkerRecord {
  id: string;
  name: string;
  role: string;
  department: string;
  supervisorName: string;
  isAuthorized: boolean;
  hasEmbedding: boolean;
  photoUrl?: string;
}

const initialWorkers: WorkerRecord[] = [
  {
    id: "W-1001",
    name: "Marcus Vance",
    role: "Haul Truck Escort",
    department: "Operations",
    supervisorName: "Sarah Connor",
    isAuthorized: false,
    hasEmbedding: true,
  },
  {
    id: "W-1002",
    name: "Elena Rostova",
    role: "Heavy Equipment Mechanic",
    department: "Maintenance",
    supervisorName: "Sarah Connor",
    isAuthorized: true,
    hasEmbedding: true,
  },
  {
    id: "W-1003",
    name: "David Chen",
    role: "Blasting Technician",
    department: "Drill & Blast",
    supervisorName: "Sarah Connor",
    isAuthorized: false,
    hasEmbedding: true,
  },
  {
    id: "W-1004",
    name: "Sarah Connor",
    role: "Safety Supervisor",
    department: "Health & Safety",
    supervisorName: "Site Director",
    isAuthorized: true,
    hasEmbedding: true,
  },
  {
    id: "W-1005",
    name: "Johnathan Price",
    role: "Field Surveyor",
    department: "Geology",
    supervisorName: "Sarah Connor",
    isAuthorized: false,
    hasEmbedding: false,
  },
];

export default function WorkersPage(): React.JSX.Element {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [showEnrollModal, setShowEnrollModal] = useState<boolean>(false);

  const filteredWorkers = initialWorkers.filter(
    (w) =>
      w.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      w.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
      w.department.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Top Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
          <span className="text-xs text-gray-400 font-mono uppercase">
            Total Monitored Personnel
          </span>
          <div className="text-2xl font-bold text-white font-mono mt-1">24</div>
        </div>
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
          <span className="text-xs text-gray-400 font-mono uppercase">
            Biometrics Enrolled (Facenet512)
          </span>
          <div className="text-2xl font-bold text-[#10B981] font-mono mt-1">
            23 <span className="text-xs text-gray-400 font-normal">(95.8%)</span>
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
          <span className="text-xs text-gray-400 font-mono uppercase">
            Authorized Mechanics
          </span>
          <div className="text-2xl font-bold text-[#00FFFF] font-mono mt-1">
            6 Active
          </div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search workers by name, role, department..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF]"
          />
        </div>

        <button
          onClick={() => setShowEnrollModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90 transition-all shadow-cyan-glow"
        >
          <Camera className="w-4 h-4" />
          <span>Enroll New Face (DeepFace)</span>
        </button>
      </div>

      {/* Workers Table */}
      <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Users className="w-4 h-4 text-[#00FFFF]" />
          Personnel Directory
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#374151] text-gray-400 font-mono uppercase text-[10px]">
                <th className="pb-3 font-semibold">Worker</th>
                <th className="pb-3 font-semibold">Role</th>
                <th className="pb-3 font-semibold">Department</th>
                <th className="pb-3 font-semibold">Supervisor</th>
                <th className="pb-3 font-semibold">Biometrics</th>
                <th className="pb-3 font-semibold">Zone Authorization</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#374151]/60">
              {filteredWorkers.map((w) => (
                <tr key={w.id} className="hover:bg-[#111827]/40 transition-colors">
                  <td className="py-3 font-medium text-white flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-[#111827] border border-[#374151] flex items-center justify-center text-gray-300">
                      <HardHat className="w-4 h-4 text-[#00FFFF]" />
                    </div>
                    <div>
                      <div className="font-semibold">{w.name}</div>
                      <div className="text-[10px] text-gray-400 font-mono">
                        {w.id}
                      </div>
                    </div>
                  </td>
                  <td className="py-3 text-gray-300">{w.role}</td>
                  <td className="py-3 text-gray-400">{w.department}</td>
                  <td className="py-3 text-gray-300">{w.supervisorName}</td>
                  <td className="py-3">
                    {w.hasEmbedding ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                        <CheckCircle2 className="w-3 h-3" />
                        512-D ENROLLED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30">
                        <XCircle className="w-3 h-3" />
                        PENDING SCAN
                      </span>
                    )}
                  </td>
                  <td className="py-3">
                    {w.isAuthorized ? (
                      <span className="inline-flex items-center gap-1 text-[#10B981] font-semibold text-[11px]">
                        <ShieldCheck className="w-4 h-4" />
                        Authorized (No Alarm)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-gray-400 text-[11px]">
                        Standard Restricted
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Biometric Face Scan Modal */}
      {showEnrollModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md p-6 rounded-2xl bg-[#1f2937] border border-[#374151] space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Camera className="w-4 h-4 text-[#00FFFF]" />
                Enroll Face Biometrics
              </h4>
              <button
                onClick={() => setShowEnrollModal(false)}
                className="text-gray-400 hover:text-white"
              >
                &times;
              </button>
            </div>
            <p className="text-xs text-gray-400">
              Upload a clear frontal photo of the personnel. DeepFace RetinaFace
              will detect facial keypoints and compute a 512-D normalized
              embedding.
            </p>

            <div className="border-2 border-dashed border-[#374151] hover:border-[#00FFFF]/50 rounded-xl p-8 text-center cursor-pointer bg-[#111827]/50">
              <Camera className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <div className="text-xs font-medium text-white">
                Drag and drop face portrait or click to browse
              </div>
              <div className="text-[10px] text-gray-500 mt-1">
                Supports JPG, PNG, WEBP (Min 200x200)
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowEnrollModal(false)}
                className="px-4 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs font-semibold text-gray-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowEnrollModal(false)}
                className="px-4 py-2 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90"
              >
                Generate 512-D Vector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
