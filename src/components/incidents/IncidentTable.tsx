"use client";

import React, { useState } from "react";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Eye,
  Mail,
  HardHat,
  Truck,
  CheckCircle2,
  Clock,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { IncidentItem } from "../../lib/api";

export type SortField =
  | "timestamp"
  | "severity"
  | "distance_meters"
  | "closing_velocity"
  | "worker_name";

export type SortDirection = "asc" | "desc";

interface IncidentTableProps {
  incidents: IncidentItem[];
  totalCount: number;
  currentPage: number;
  pageSize: number;
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onSelectIncident: (incident: IncidentItem) => void;
  onNotifySupervisor: (incidentId: number) => Promise<void>;
  isLoading: boolean;
}

export default function IncidentTable({
  incidents,
  totalCount,
  currentPage,
  pageSize,
  sortField,
  sortDirection,
  onSort,
  onPageChange,
  onPageSizeChange,
  onSelectIncident,
  onNotifySupervisor,
  isLoading,
}: IncidentTableProps): React.JSX.Element {
  const [notifyingIds, setNotifyingIds] = useState<Set<number>>(new Set());

  const handleNotifyClick = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setNotifyingIds((prev) => new Set(prev).add(id));
    try {
      await onNotifySupervisor(id);
    } finally {
      setNotifyingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const startRow = (currentPage - 1) * pageSize + 1;
  const endRow = Math.min(totalCount, currentPage * pageSize);

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 text-gray-500" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="w-3 h-3 text-[#00FFFF]" />
    ) : (
      <ArrowDown className="w-3 h-3 text-[#00FFFF]" />
    );
  };

  return (
    <div className="rounded-2xl bg-[#1f2937]/90 backdrop-blur-md border border-[#374151] shadow-xl overflow-hidden">
      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-[#374151] text-gray-400 font-mono uppercase text-[11px] bg-[#111827]/60">
              <th className="py-3.5 px-4 font-semibold">Incident ID</th>
              <th
                onClick={() => onSort("timestamp")}
                className="py-3.5 px-4 font-semibold cursor-pointer hover:text-white transition-colors select-none"
              >
                <div className="flex items-center gap-1.5">
                  <span>Timestamp (UTC)</span>
                  {renderSortIcon("timestamp")}
                </div>
              </th>
              <th
                onClick={() => onSort("worker_name")}
                className="py-3.5 px-4 font-semibold cursor-pointer hover:text-white transition-colors select-none"
              >
                <div className="flex items-center gap-1.5">
                  <span>Personnel</span>
                  {renderSortIcon("worker_name")}
                </div>
              </th>
              <th className="py-3.5 px-4 font-semibold">Equipment</th>
              <th
                onClick={() => onSort("distance_meters")}
                className="py-3.5 px-4 font-semibold cursor-pointer hover:text-white transition-colors select-none"
              >
                <div className="flex items-center gap-1.5">
                  <span>Proximity</span>
                  {renderSortIcon("distance_meters")}
                </div>
              </th>
              <th
                onClick={() => onSort("closing_velocity")}
                className="py-3.5 px-4 font-semibold cursor-pointer hover:text-white transition-colors select-none"
              >
                <div className="flex items-center gap-1.5">
                  <span>Velocity</span>
                  {renderSortIcon("closing_velocity")}
                </div>
              </th>
              <th
                onClick={() => onSort("severity")}
                className="py-3.5 px-4 font-semibold cursor-pointer hover:text-white transition-colors select-none"
              >
                <div className="flex items-center gap-1.5">
                  <span>Severity</span>
                  {renderSortIcon("severity")}
                </div>
              </th>
              <th className="py-3.5 px-4 font-semibold">Supervisor Alert</th>
              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-[#374151]/50">
            {isLoading ? (
              [1, 2, 3, 4, 5].map((i) => (
                <tr key={i} className="animate-pulse">
                  <td colSpan={9} className="py-4 px-4">
                    <div className="h-6 rounded bg-[#111827]/70" />
                  </td>
                </tr>
              ))
            ) : incidents.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-gray-400 text-xs">
                  <Clock className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                  <p className="font-semibold text-white">No Incidents Found</p>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    No records match the current filter criteria.
                  </p>
                </td>
              </tr>
            ) : (
              incidents.map((inc) => {
                const isCritical = inc.severity === "CRITICAL";
                const isWarning = inc.severity === "WARNING";
                const isNotifying = notifyingIds.has(inc.id);

                return (
                  <tr
                    key={inc.id}
                    onClick={() => onSelectIncident(inc)}
                    className="hover:bg-[#111827]/50 cursor-pointer transition-colors group"
                  >
                    {/* Incident ID */}
                    <td className="py-3.5 px-4 font-mono font-bold text-white">
                      <span className="px-2 py-0.5 rounded bg-[#111827] border border-[#374151] group-hover:border-[#00FFFF]/40 transition-colors">
                        INC-{inc.id.toString().padStart(4, "0")}
                      </span>
                    </td>

                    {/* Timestamp */}
                    <td className="py-3.5 px-4 font-mono text-gray-300">
                      <div>
                        {new Date(inc.timestamp).toISOString().replace("T", " ").substring(0, 19)}
                      </div>
                      <div className="text-[10px] text-gray-500">
                        Sector: {inc.zone}
                      </div>
                    </td>

                    {/* Worker */}
                    <td className="py-3.5 px-4">
                      {inc.worker_name ? (
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-lg bg-[#111827] border border-[#374151] flex items-center justify-center text-gray-300">
                            <HardHat className="w-3.5 h-3.5 text-[#00FFFF]" />
                          </div>
                          <div>
                            <div className="font-semibold text-white">
                              {inc.worker_name}
                            </div>
                            <div className="text-[10px] text-gray-400 font-mono">
                              ID #{inc.worker_id}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-gray-500 italic font-mono text-[11px]">
                          Unidentified Personnel
                        </span>
                      )}
                    </td>

                    {/* Machine */}
                    <td className="py-3.5 px-4 font-mono text-gray-300">
                      <div className="flex items-center gap-1.5">
                        <Truck className="w-3.5 h-3.5 text-gray-400" />
                        <span>CAT-797F-0{inc.machine_id}</span>
                      </div>
                    </td>

                    {/* Distance */}
                    <td className="py-3.5 px-4 font-mono">
                      <span
                        className={`font-bold text-sm ${
                          inc.distance_meters < 3.0
                            ? "text-[#FF3B30]"
                            : inc.distance_meters < 10.0
                            ? "text-[#F59E0B]"
                            : "text-[#10B981]"
                        }`}
                      >
                        {inc.distance_meters.toFixed(1)} m
                      </span>
                    </td>

                    {/* Velocity */}
                    <td className="py-3.5 px-4 font-mono text-gray-300">
                      {inc.closing_velocity ? (
                        <span className="font-semibold">
                          {inc.closing_velocity.toFixed(1)} m/s
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>

                    {/* Severity Badge */}
                    <td className="py-3.5 px-4 font-mono">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          isCritical
                            ? "bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30 shadow-[0_0_8px_rgba(255,59,48,0.2)]"
                            : isWarning
                            ? "bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30"
                            : "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                        }`}
                      >
                        {inc.severity}
                      </span>
                    </td>

                    {/* Supervisor Notified */}
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      {inc.supervisor_notified ? (
                        <span className="inline-flex items-center gap-1 text-[#10B981] font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Sent
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-gray-500">
                          Pending
                        </span>
                      )}
                    </td>

                    {/* Action Buttons */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectIncident(inc);
                          }}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/50 text-gray-300 hover:text-[#00FFFF] transition-all font-mono text-[11px]"
                          title="Inspect Incident Clip"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Clip</span>
                        </button>

                        <button
                          onClick={(e) => handleNotifyClick(e, inc.id)}
                          disabled={isNotifying}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#F59E0B]/50 text-gray-300 hover:text-[#F59E0B] transition-all font-mono text-[11px] disabled:opacity-50"
                          title="Dispatch Supervisor Alert"
                        >
                          {isNotifying ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Mail className="w-3.5 h-3.5" />
                          )}
                          <span>Notify</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-[#374151]/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono text-gray-400">
        <div className="flex items-center gap-2">
          <span>Rows per page:</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(parseInt(e.target.value, 10))}
            className="px-2 py-1 rounded-lg bg-[#111827] border border-[#374151] text-white focus:outline-none focus:border-[#00FFFF]"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
          <span className="ml-2">
            Showing {totalCount === 0 ? 0 : startRow} - {endRow} of {totalCount} records
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1 || isLoading}
            className="p-1.5 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/40 text-gray-300 hover:text-white disabled:opacity-40 disabled:hover:border-[#374151]"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-3 py-1 rounded-lg bg-[#111827] border border-[#374151] text-white">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages || isLoading}
            className="p-1.5 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/40 text-gray-300 hover:text-white disabled:opacity-40 disabled:hover:border-[#374151]"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
