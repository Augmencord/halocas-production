"use client";

import React from "react";
import {
  Search,
  LayoutGrid,
  List,
  UserPlus,
  ShieldCheck,
  ShieldAlert,
  Fingerprint,
  Filter,
} from "lucide-react";
import { WorkerFilterParams } from "@/lib/api";

interface WorkerFiltersProps {
  filters: WorkerFilterParams;
  viewMode: "grid" | "table";
  departments: string[];
  totalResults: number;
  onFilterChange: (newFilters: Partial<WorkerFilterParams>) => void;
  onViewModeChange: (mode: "grid" | "table") => void;
  onOpenAddModal: () => void;
}

export function WorkerFilters({
  filters,
  viewMode,
  departments,
  totalResults,
  onFilterChange,
  onViewModeChange,
  onOpenAddModal,
}: WorkerFiltersProps): React.JSX.Element {
  return (
    <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-4 backdrop-blur-md shadow-lg">
      {/* Top Search & Primary Action Row */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-xl">
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by worker name, role, department, or badge ID (e.g. W-1001)..."
            value={filters.search || ""}
            onChange={(e) => onFilterChange({ search: e.target.value, offset: 0 })}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF] transition-colors"
          />
          {filters.search && (
            <button
              onClick={() => onFilterChange({ search: "", offset: 0 })}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-xs font-mono"
            >
              Clear
            </button>
          )}
        </div>

        {/* View Mode & Add Worker Action */}
        <div className="flex items-center gap-3 self-end lg:self-auto">
          {/* View Toggle */}
          <div className="flex items-center rounded-xl bg-[#111827] border border-[#374151] p-1">
            <button
              onClick={() => onViewModeChange("grid")}
              className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === "grid"
                  ? "bg-[#00FFFF] text-[#111827] shadow-sm font-bold"
                  : "text-gray-400 hover:text-white"
              }`}
              title="Grid View"
            >
              <LayoutGrid className="w-4 h-4" />
              <span className="hidden sm:inline">Grid</span>
            </button>
            <button
              onClick={() => onViewModeChange("table")}
              className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === "table"
                  ? "bg-[#00FFFF] text-[#111827] shadow-sm font-bold"
                  : "text-gray-400 hover:text-white"
              }`}
              title="Table View"
            >
              <List className="w-4 h-4" />
              <span className="hidden sm:inline">Table</span>
            </button>
          </div>

          {/* Add Worker CTA */}
          <button
            onClick={onOpenAddModal}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90 transition-all shadow-md shadow-[#00FFFF]/20 active:scale-95"
          >
            <UserPlus className="w-4 h-4" />
            <span>Enroll New Worker</span>
          </button>
        </div>
      </div>

      {/* Filter Chips & Department Dropdown Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-[#374151]/50 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Department Dropdown */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={filters.department || "ALL"}
              onChange={(e) =>
                onFilterChange({ department: e.target.value, offset: 0 })
              }
              className="bg-[#111827] border border-[#374151] text-gray-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-[#00FFFF]"
            >
              <option value="ALL">All Departments</option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>

          {/* Biometrics Status Pills */}
          <div className="flex items-center gap-1 bg-[#111827]/70 p-0.5 rounded-lg border border-[#374151]">
            <button
              onClick={() => onFilterChange({ biometrics: "ALL", offset: 0 })}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                (filters.biometrics || "ALL") === "ALL"
                  ? "bg-[#374151] text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              All Biometrics
            </button>
            <button
              onClick={() => onFilterChange({ biometrics: "ENROLLED", offset: 0 })}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium flex items-center gap-1 transition-colors ${
                filters.biometrics === "ENROLLED"
                  ? "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/40"
                  : "text-gray-400 hover:text-[#10B981]"
              }`}
            >
              <Fingerprint className="w-3 h-3" />
              512-D Enrolled
            </button>
            <button
              onClick={() => onFilterChange({ biometrics: "PENDING", offset: 0 })}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                filters.biometrics === "PENDING"
                  ? "bg-[#FF3B30]/20 text-[#FF3B30] border border-[#FF3B30]/40"
                  : "text-gray-400 hover:text-[#FF3B30]"
              }`}
            >
              Pending Scan
            </button>
          </div>

          {/* Hazard Authorization Pills */}
          <div className="flex items-center gap-1 bg-[#111827]/70 p-0.5 rounded-lg border border-[#374151]">
            <button
              onClick={() => onFilterChange({ authorization: "ALL", offset: 0 })}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                (filters.authorization || "ALL") === "ALL"
                  ? "bg-[#374151] text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              All Zones
            </button>
            <button
              onClick={() =>
                onFilterChange({ authorization: "AUTHORIZED", offset: 0 })
              }
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium flex items-center gap-1 transition-colors ${
                filters.authorization === "AUTHORIZED"
                  ? "bg-[#00FFFF]/20 text-[#00FFFF] border border-[#00FFFF]/40"
                  : "text-gray-400 hover:text-[#00FFFF]"
              }`}
            >
              <ShieldCheck className="w-3 h-3" />
              Authorized
            </button>
            <button
              onClick={() =>
                onFilterChange({ authorization: "RESTRICTED", offset: 0 })
              }
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium flex items-center gap-1 transition-colors ${
                filters.authorization === "RESTRICTED"
                  ? "bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40"
                  : "text-gray-400 hover:text-[#F59E0B]"
              }`}
            >
              <ShieldAlert className="w-3 h-3" />
              Restricted
            </button>
          </div>
        </div>

        {/* Results Counter */}
        <div className="text-gray-400 text-xs font-mono">
          Showing <span className="text-white font-bold">{totalResults}</span> personnel
        </div>
      </div>
    </div>
  );
}
