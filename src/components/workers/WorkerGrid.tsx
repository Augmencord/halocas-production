"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import {
  HardHat,
  Fingerprint,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  ChevronRight,
  Mail,
  UserX,
} from "lucide-react";
import { WorkerItem } from "@/lib/api";

interface WorkerGridProps {
  workers: WorkerItem[];
  isLoading: boolean;
}

export function WorkerGrid({
  workers,
  isLoading,
}: WorkerGridProps): React.JSX.Element {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, idx) => (
          <div
            key={idx}
            className="p-5 rounded-2xl bg-[#1f2937]/50 border border-[#374151]/60 animate-pulse space-y-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gray-700" />
              <div className="space-y-2 flex-1">
                <div className="h-4 bg-gray-700 rounded w-3/4" />
                <div className="h-3 bg-gray-800 rounded w-1/2" />
              </div>
            </div>
            <div className="h-8 bg-gray-800 rounded-lg w-full" />
            <div className="h-6 bg-gray-800 rounded w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  if (workers.length === 0) {
    return (
      <div className="p-12 rounded-2xl bg-[#1f2937]/70 border border-[#374151] text-center space-y-3">
        <UserX className="w-10 h-10 text-gray-500 mx-auto" />
        <h3 className="text-base font-bold text-white">No Personnel Found</h3>
        <p className="text-xs text-gray-400 max-w-sm mx-auto">
          No workers match your current search terms or active filters. Try adjusting your filters or search query.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {workers.map((worker) => (
        <div
          key={worker.id}
          className="group relative p-5 rounded-2xl bg-[#1f2937]/90 border border-[#374151] hover:border-[#00FFFF]/50 hover:bg-[#1f2937] transition-all duration-200 shadow-md hover:shadow-cyan-glow/10 flex flex-col justify-between space-y-4"
        >
          {/* Header with Photo, Name, Badge */}
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                {/* Photo / Avatar */}
                <div className="relative w-12 h-12 rounded-xl bg-[#111827] border border-[#374151] overflow-hidden flex items-center justify-center shrink-0">
                  {worker.face_photo_url ? (
                    <Image
                      src={worker.face_photo_url}
                      alt={worker.name}
                      width={48}
                      height={48}
                      className="w-full h-full object-cover"
                      unoptimized
                    />
                  ) : (
                    <div className="text-gray-400 font-bold font-mono text-sm">
                      {worker.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </div>
                  )}

                  {/* Authorization Dot Indicator */}
                  <span
                    className={`absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full border-2 border-[#1f2937] ${
                      worker.is_authorized ? "bg-[#10B981]" : "bg-[#F59E0B]"
                    }`}
                    title={
                      worker.is_authorized
                        ? "Hazardous Machinery Authorized"
                        : "Restricted Personnel"
                    }
                  />
                </div>

                <div className="min-w-0">
                  <div className="font-bold text-white text-sm truncate group-hover:text-[#00FFFF] transition-colors">
                    {worker.name}
                  </div>
                  <div className="text-[11px] text-gray-400 font-mono">
                    W-{worker.id}
                  </div>
                </div>
              </div>

              {/* Department Pill */}
              <span className="px-2 py-0.5 rounded-md bg-[#111827] border border-[#374151] text-[10px] font-mono text-gray-300 shrink-0">
                {worker.department}
              </span>
            </div>

            {/* Role & Supervisor */}
            <div className="space-y-1 text-xs">
              <div className="text-gray-300 font-medium flex items-center gap-1.5 truncate">
                <HardHat className="w-3.5 h-3.5 text-[#00FFFF] shrink-0" />
                <span className="truncate">{worker.role}</span>
              </div>
              {worker.supervisor_email && (
                <div className="text-gray-400 text-[11px] flex items-center gap-1.5 truncate">
                  <Mail className="w-3 h-3 text-gray-500 shrink-0" />
                  <span className="truncate">{worker.supervisor_email}</span>
                </div>
              )}
            </div>

            {/* Badges: Biometrics & Zone Authorization */}
            <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-[#374151]/50">
              {/* Biometrics Badge */}
              {worker.has_face_embedding ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  <Fingerprint className="w-3 h-3" />
                  512-D ENROLLED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30">
                  PENDING SCAN
                </span>
              )}

              {/* Zone Authorization Badge */}
              {worker.is_authorized ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#00FFFF]/15 text-[#00FFFF] border border-[#00FFFF]/30">
                  <ShieldCheck className="w-3 h-3" />
                  AUTHORIZED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-800 text-gray-400 border border-gray-700">
                  <ShieldAlert className="w-3 h-3" />
                  RESTRICTED
                </span>
              )}
            </div>
          </div>

          {/* Footer: Infraction Count & View Profile Link */}
          <div className="pt-2 border-t border-[#374151]/50 flex items-center justify-between text-xs">
            <div className="flex items-center gap-1 text-[11px] text-gray-400 font-mono">
              <AlertTriangle
                className={`w-3.5 h-3.5 ${
                  (worker.total_incidents || 0) > 0
                    ? "text-[#FF3B30]"
                    : "text-gray-500"
                }`}
              />
              <span>
                {worker.total_incidents || 0}{" "}
                {(worker.total_incidents || 0) === 1 ? "breach" : "breaches"}
              </span>
            </div>

            <Link
              href={`/workers/${worker.id}`}
              className="inline-flex items-center gap-1 text-[#00FFFF] hover:text-[#00FFFF]/80 font-bold text-xs group-hover:translate-x-0.5 transition-transform"
            >
              <span>Dossier</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      ))}
    </div>
  );
}
