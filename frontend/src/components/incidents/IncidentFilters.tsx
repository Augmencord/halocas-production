"use client";

import React from "react";
import {
  Search,
  RotateCcw,
  Download,
  Calendar,
  Truck,
  MapPin,
  X,
} from "lucide-react";
import { IncidentFilterParams } from "../../lib/api";

interface IncidentFiltersProps {
  filters: IncidentFilterParams;
  onFilterChange: (newFilters: Partial<IncidentFilterParams>) => void;
  onReset: () => void;
  onExportCSV: () => void;
  totalFiltered: number;
}

const machines = [
  { id: "ALL", label: "All Machines" },
  { id: "CAT-797F-01", label: "CAT-797F #1 (Haul Truck)" },
  { id: "KOMATSU-930E-03", label: "Komatsu 930E #3 (Haul Truck)" },
  { id: "HITACHI-EX8000-02", label: "Hitachi EX8000 #2 (Shovel)" },
  { id: "CAT-994K-05", label: "CAT-994K #5 (Loader)" },
];

const zones = [
  { id: "ALL", label: "All Mining Zones" },
  { id: "Sector 04 - North Cut", label: "Sector 04 - North Cut" },
  { id: "Haul Road Alpha", label: "Haul Road Alpha" },
  { id: "Sector 04 - Bench 3", label: "Sector 04 - Bench 3" },
  { id: "Stockpile Bravo", label: "Stockpile Bravo" },
  { id: "Waste Dump Charlie", label: "Waste Dump Charlie" },
];

export default function IncidentFilters({
  filters,
  onFilterChange,
  onReset,
  onExportCSV,
  totalFiltered,
}: IncidentFiltersProps): React.JSX.Element {
  return (
    <div className="p-5 rounded-2xl bg-[#1f2937]/90 backdrop-blur-md border border-[#374151] shadow-xl space-y-4">
      {/* Top Row: Search & Severity Pills & Export Button */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Worker & Keyword Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by worker name, personnel ID, or incident..."
            value={filters.worker_search || ""}
            onChange={(e) =>
              onFilterChange({ worker_search: e.target.value, offset: 0 })
            }
            className="w-full pl-10 pr-9 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF] transition-all font-mono"
          />
          {filters.worker_search && (
            <button
              onClick={() => onFilterChange({ worker_search: "", offset: 0 })}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Severity Tier Selector */}
        <div className="flex items-center gap-1.5 bg-[#111827] p-1 rounded-xl border border-[#374151]">
          {(["ALL", "CRITICAL", "WARNING", "CAUTION"] as const).map((sev) => {
            const isSelected = (filters.severity || "ALL") === sev;
            return (
              <button
                key={sev}
                onClick={() =>
                  onFilterChange({
                    severity: sev === "ALL" ? undefined : sev,
                    offset: 0,
                  })
                }
                className={`px-3 py-1.5 text-xs font-mono font-bold rounded-lg transition-all ${
                  isSelected
                    ? sev === "CRITICAL"
                      ? "bg-[#FF3B30] text-white shadow-[0_0_12px_rgba(255,59,48,0.4)]"
                      : sev === "WARNING"
                      ? "bg-[#F59E0B] text-[#111827] shadow-[0_0_12px_rgba(245,158,11,0.4)]"
                      : sev === "CAUTION"
                      ? "bg-blue-500 text-white"
                      : "bg-[#00FFFF] text-[#111827] shadow-cyan-glow"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {sev}
              </button>
            );
          })}
        </div>

        {/* Actions: Reset & Export CSV */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#111827] border border-[#374151] hover:border-gray-400 text-xs font-mono text-gray-300 hover:text-white transition-all"
            title="Reset Filters"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Reset</span>
          </button>

          <button
            onClick={onExportCSV}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#10B981] hover:bg-[#10B981]/90 text-[#111827] text-xs font-bold font-mono transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:scale-[1.02]"
          >
            <Download className="w-4 h-4 text-[#111827]" />
            <span>Export CSV ({totalFiltered})</span>
          </button>
        </div>
      </div>

      {/* Bottom Row: Machine Filter, Zone Filter, Date Range */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-3 border-t border-[#374151]/60 text-xs">
        {/* Machine Filter Dropdown */}
        <div className="space-y-1">
          <label className="text-gray-400 font-mono text-[11px] flex items-center gap-1">
            <Truck className="w-3 h-3 text-[#00FFFF]" />
            Machine Asset
          </label>
          <select
            value={filters.machine_id || "ALL"}
            onChange={(e) =>
              onFilterChange({
                machine_id: e.target.value === "ALL" ? undefined : e.target.value,
                offset: 0,
              })
            }
            className="w-full px-3 py-2 rounded-xl bg-[#111827] border border-[#374151] text-gray-200 font-mono focus:outline-none focus:border-[#00FFFF]"
          >
            {machines.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {/* Zone Filter Dropdown */}
        <div className="space-y-1">
          <label className="text-gray-400 font-mono text-[11px] flex items-center gap-1">
            <MapPin className="w-3 h-3 text-[#00FFFF]" />
            Mining Sector
          </label>
          <select
            value={filters.zone || "ALL"}
            onChange={(e) =>
              onFilterChange({
                zone: e.target.value === "ALL" ? undefined : e.target.value,
                offset: 0,
              })
            }
            className="w-full px-3 py-2 rounded-xl bg-[#111827] border border-[#374151] text-gray-200 font-mono focus:outline-none focus:border-[#00FFFF]"
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date Range Preset */}
        <div className="space-y-1">
          <label className="text-gray-400 font-mono text-[11px] flex items-center gap-1">
            <Calendar className="w-3 h-3 text-[#00FFFF]" />
            Time Horizon
          </label>
          <select
            value={filters.date_range || "all"}
            onChange={(e) =>
              onFilterChange({
                date_range: e.target.value as IncidentFilterParams["date_range"],
                offset: 0,
              })
            }
            className="w-full px-3 py-2 rounded-xl bg-[#111827] border border-[#374151] text-gray-200 font-mono focus:outline-none focus:border-[#00FFFF]"
          >
            <option value="all">All Available Shifts</option>
            <option value="today">Today (Since Midnight UTC)</option>
            <option value="24h">Past 24 Hours</option>
            <option value="7d">Past 7 Days</option>
            <option value="custom">Custom Date Range</option>
          </select>
        </div>

        {/* Custom Start/End Date Inputs (if custom is selected) */}
        {filters.date_range === "custom" ? (
          <div className="flex items-center gap-2">
            <div className="flex-1 space-y-1">
              <label className="text-gray-400 font-mono text-[10px]">Start Date</label>
              <input
                type="date"
                value={filters.start_date || ""}
                onChange={(e) =>
                  onFilterChange({ start_date: e.target.value, offset: 0 })
                }
                className="w-full px-2 py-1.5 rounded-xl bg-[#111827] border border-[#374151] text-gray-200 font-mono text-xs focus:outline-none focus:border-[#00FFFF]"
              />
            </div>
            <div className="flex-1 space-y-1">
              <label className="text-gray-400 font-mono text-[10px]">End Date</label>
              <input
                type="date"
                value={filters.end_date || ""}
                onChange={(e) =>
                  onFilterChange({ end_date: e.target.value, offset: 0 })
                }
                className="w-full px-2 py-1.5 rounded-xl bg-[#111827] border border-[#374151] text-gray-200 font-mono text-xs focus:outline-none focus:border-[#00FFFF]"
              />
            </div>
          </div>
        ) : (
          <div className="flex items-end pb-1">
            <div className="text-[11px] font-mono text-gray-400">
              Active Scope: <strong className="text-white">{totalFiltered} Records</strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
