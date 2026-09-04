"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Fingerprint,
  ShieldCheck,
  ShieldAlert,
  ArrowUpDown,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  UserX,
} from "lucide-react";
import { WorkerItem } from "@/lib/api";

interface WorkerTableProps {
  workers: WorkerItem[];
  totalCount: number;
  offset: number;
  limit: number;
  isLoading: boolean;
  onPageChange: (newOffset: number) => void;
  onLimitChange: (newLimit: number) => void;
}

type SortField = "name" | "department" | "role" | "total_incidents";

export function WorkerTable({
  workers,
  totalCount,
  offset,
  limit,
  isLoading,
  onPageChange,
  onLimitChange,
}: WorkerTableProps): React.JSX.Element {
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  const handleSort = (field: SortField): void => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const sortedWorkers = [...workers].sort((a, b) => {
    let comp = 0;
    if (sortField === "name") {
      comp = a.name.localeCompare(b.name);
    } else if (sortField === "department") {
      comp = a.department.localeCompare(b.department);
    } else if (sortField === "role") {
      comp = a.role.localeCompare(b.role);
    } else if (sortField === "total_incidents") {
      comp = (a.total_incidents || 0) - (b.total_incidents || 0);
    }
    return sortAsc ? comp : -comp;
  });

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(totalCount / limit) || 1;

  if (isLoading) {
    return (
      <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4">
        <div className="h-6 bg-gray-800 rounded w-1/4 animate-pulse" />
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-12 bg-gray-850 rounded-xl animate-pulse bg-gray-800/40"
            />
          ))}
        </div>
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
    <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4 backdrop-blur-md shadow-lg">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-[#374151] text-gray-400 font-mono uppercase text-[10px]">
              <th
                onClick={() => handleSort("name")}
                className="pb-3 font-semibold cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center gap-1">
                  <span>Personnel</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th
                onClick={() => handleSort("role")}
                className="pb-3 font-semibold cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center gap-1">
                  <span>Role</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th
                onClick={() => handleSort("department")}
                className="pb-3 font-semibold cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center gap-1">
                  <span>Department</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="pb-3 font-semibold">Supervisor Contact</th>
              <th className="pb-3 font-semibold">Biometrics (Facenet512)</th>
              <th className="pb-3 font-semibold">Zone Authorization</th>
              <th
                onClick={() => handleSort("total_incidents")}
                className="pb-3 font-semibold cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center gap-1">
                  <span>Breaches</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="pb-3 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#374151]/50">
            {sortedWorkers.map((worker) => (
              <tr
                key={worker.id}
                className="hover:bg-[#111827]/40 transition-colors group"
              >
                {/* Personnel */}
                <td className="py-3.5 pr-3 font-medium text-white">
                  <div className="flex items-center gap-3">
                    <div className="relative w-8 h-8 rounded-lg bg-[#111827] border border-[#374151] overflow-hidden flex items-center justify-center shrink-0">
                      {worker.face_photo_url ? (
                        <Image
                          src={worker.face_photo_url}
                          alt={worker.name}
                          width={32}
                          height={32}
                          className="w-full h-full object-cover"
                          unoptimized
                        />
                      ) : (
                        <span className="text-gray-400 font-mono font-bold text-xs">
                          {worker.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </span>
                      )}
                    </div>
                    <div>
                      <Link
                        href={`/workers/${worker.id}`}
                        className="font-bold hover:text-[#00FFFF] transition-colors"
                      >
                        {worker.name}
                      </Link>
                      <div className="text-[10px] text-gray-400 font-mono">
                        W-{worker.id}
                      </div>
                    </div>
                  </div>
                </td>

                {/* Role */}
                <td className="py-3.5 pr-3 text-gray-300 font-medium">
                  {worker.role}
                </td>

                {/* Department */}
                <td className="py-3.5 pr-3">
                  <span className="px-2 py-0.5 rounded-md bg-[#111827] border border-[#374151] text-[10px] font-mono text-gray-300">
                    {worker.department}
                  </span>
                </td>

                {/* Supervisor */}
                <td className="py-3.5 pr-3 text-gray-400 font-mono text-[11px]">
                  {worker.supervisor_email || "N/A"}
                </td>

                {/* Biometrics */}
                <td className="py-3.5 pr-3">
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
                </td>

                {/* Zone Authorization */}
                <td className="py-3.5 pr-3">
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
                </td>

                {/* Breaches */}
                <td className="py-3.5 pr-3 font-mono">
                  <span
                    className={`font-bold ${
                      (worker.total_incidents || 0) > 0
                        ? "text-[#FF3B30]"
                        : "text-gray-400"
                    }`}
                  >
                    {worker.total_incidents || 0}
                  </span>
                </td>

                {/* Actions */}
                <td className="py-3.5 text-right">
                  <Link
                    href={`/workers/${worker.id}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF] text-gray-300 hover:text-[#00FFFF] text-xs font-semibold transition-colors"
                  >
                    <span>Dossier</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-[#374151]/60 text-xs">
        <div className="flex items-center gap-2 text-gray-400">
          <span>Rows per page:</span>
          <select
            value={limit}
            onChange={(e) => onLimitChange(parseInt(e.target.value, 10))}
            className="bg-[#111827] border border-[#374151] text-white rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-[#00FFFF]"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
          <span className="font-mono text-gray-400 ml-2">
            Showing {Math.min(offset + 1, totalCount)} -{" "}
            {Math.min(offset + limit, totalCount)} of {totalCount}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onPageChange(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="p-1.5 rounded-lg bg-[#111827] border border-[#374151] text-gray-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Previous Page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="px-3 py-1 font-mono text-xs text-gray-300">
            Page {currentPage} of {totalPages}
          </span>

          <button
            onClick={() => onPageChange(offset + limit)}
            disabled={offset + limit >= totalCount}
            className="p-1.5 rounded-lg bg-[#111827] border border-[#374151] text-gray-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Next Page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
