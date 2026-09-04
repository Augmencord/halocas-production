"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Users,
  Fingerprint,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  X,
} from "lucide-react";
import {
  fetchWorkers,
  WorkerItem,
  WorkerFilterParams,
} from "@/lib/api";
import { WorkerFilters } from "@/components/workers/WorkerFilters";
import { WorkerGrid } from "@/components/workers/WorkerGrid";
import { WorkerTable } from "@/components/workers/WorkerTable";
import { AddWorkerModal } from "@/components/workers/AddWorkerModal";

interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

export default function WorkersPage(): React.JSX.Element {
  const [workers, setWorkers] = useState<WorkerItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // View Mode: grid vs table
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // Filters
  const [filters, setFilters] = useState<WorkerFilterParams>({
    search: "",
    department: "ALL",
    biometrics: "ALL",
    authorization: "ALL",
    offset: 0,
    limit: 12,
  });

  // Add Worker Modal
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);

  // Toasts
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (type: "success" | "error" | "info", message: string): void => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id: string): void => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Extract unique departments
  const availableDepartments = useMemo(() => {
    const depts = new Set<string>([
      "Operations",
      "Maintenance",
      "Drill & Blast",
      "Health & Safety",
      "Geology",
      "Logistics",
    ]);
    workers.forEach((w) => {
      if (w.department) depts.add(w.department);
    });
    return Array.from(depts);
  }, [workers]);

  useEffect(() => {
    let active = true;

    const run = async (): Promise<void> => {
      try {
        const res = await fetchWorkers(filters);
        if (active) {
          setWorkers(res.workers);
          setTotalCount(res.totalCount);
          setError(null);
          setIsLoading(false);
        }
      } catch (err) {
        if (active) {
          const msg =
            err instanceof Error ? err.message : "Failed to load mine personnel";
          setError(msg);
          setIsLoading(false);
        }
      }
    };

    void run();

    return () => {
      active = false;
    };
  }, [filters]);

  const handleFilterChange = (newFilters: Partial<WorkerFilterParams>): void => {
    setIsLoading(true);
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  const handleRefresh = (): void => {
    setIsLoading(true);
    setFilters((prev) => ({ ...prev }));
  };

  const handleWorkerCreated = (newWorker: WorkerItem): void => {
    addToast(
      "success",
      `Worker ${newWorker.name} (W-${newWorker.id}) registered successfully with biometrics!`
    );
    setIsLoading(true);
    setFilters((prev) => ({ ...prev }));
  };

  // Metrics computation
  const totalMonitored = totalCount || workers.length;
  const enrolledCount = workers.filter((w) => w.has_face_embedding).length;
  const enrolledPercent =
    totalMonitored > 0
      ? Math.round((enrolledCount / totalMonitored) * 100)
      : 0;
  const authorizedCount = workers.filter((w) => w.is_authorized).length;
  const breachCount = workers.filter((w) => (w.total_incidents || 0) > 0).length;

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Stack */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center gap-2 px-4 py-2.5 rounded-xl border text-xs font-semibold shadow-2xl backdrop-blur-md transition-all ${
              toast.type === "success"
                ? "bg-[#10B981]/20 border-[#10B981] text-[#10B981]"
                : toast.type === "error"
                ? "bg-[#FF3B30]/20 border-[#FF3B30] text-[#FF3B30]"
                : "bg-[#00FFFF]/20 border-[#00FFFF] text-[#00FFFF]"
            }`}
          >
            {toast.type === "success" ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            <span>{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="ml-2 hover:opacity-75"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* Header & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-gray-400 uppercase tracking-wider mb-1">
            <Users className="w-4 h-4 text-[#00FFFF]" />
            <span>Workforce Safety & Biometrics</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Personnel Directory
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Monitor mine site personnel, manage hazard zone clearances, and verify DeepFace 512-D biometrics.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#1f2937] border border-[#374151] hover:border-[#00FFFF] text-gray-300 hover:text-white text-xs font-semibold self-start sm:self-auto transition-colors"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#00FFFF]" : ""}`}
          />
          <span>Refresh Directory</span>
        </button>
      </div>

      {/* Top Metrics Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Monitored */}
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-400 font-mono uppercase">
            <span>Total Personnel</span>
            <Users className="w-4 h-4 text-[#00FFFF]" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {totalMonitored}
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            Across 6 operational sectors
          </div>
        </div>

        {/* Biometrics Enrolled */}
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-400 font-mono uppercase">
            <span>512-D Biometrics</span>
            <Fingerprint className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="text-2xl font-bold text-[#10B981] font-mono">
            {enrolledPercent}%
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            {enrolledCount} of {totalMonitored} enrolled in Facenet512
          </div>
        </div>

        {/* Hazard Authorized */}
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-400 font-mono uppercase">
            <span>Hazard Authorized</span>
            <ShieldCheck className="w-4 h-4 text-[#00FFFF]" />
          </div>
          <div className="text-2xl font-bold text-[#00FFFF] font-mono">
            {authorizedCount} Active
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            Heavy machinery proximity clearance
          </div>
        </div>

        {/* Recorded Breaches */}
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-400 font-mono uppercase">
            <span>Recorded Breaches</span>
            <AlertTriangle className="w-4 h-4 text-[#FF3B30]" />
          </div>
          <div className="text-2xl font-bold text-[#FF3B30] font-mono">
            {breachCount} Flagged
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            Personnel with proximity events
          </div>
        </div>
      </div>

      {/* Filter & Control Bar */}
      <WorkerFilters
        filters={filters}
        viewMode={viewMode}
        departments={availableDepartments}
        totalResults={totalCount}
        onFilterChange={handleFilterChange}
        onViewModeChange={setViewMode}
        onOpenAddModal={() => setIsAddModalOpen(true)}
      />

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-2xl bg-[#FF3B30]/15 border border-[#FF3B30]/40 flex items-center justify-between text-xs text-[#FF3B30]">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={handleRefresh}
            className="px-3 py-1 rounded-lg bg-[#FF3B30]/20 hover:bg-[#FF3B30]/30 font-bold transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Directory Content (Grid or Table) */}
      {viewMode === "grid" ? (
        <WorkerGrid workers={workers} isLoading={isLoading} />
      ) : (
        <WorkerTable
          workers={workers}
          totalCount={totalCount}
          offset={filters.offset || 0}
          limit={filters.limit || 12}
          isLoading={isLoading}
          onPageChange={(newOffset) => handleFilterChange({ offset: newOffset })}
          onLimitChange={(newLimit) =>
            handleFilterChange({ limit: newLimit, offset: 0 })
          }
        />
      )}

      {/* Add Worker Biometric Modal */}
      <AddWorkerModal
        isOpen={isAddModalOpen}
        departments={availableDepartments}
        onClose={() => setIsAddModalOpen(false)}
        onSuccess={handleWorkerCreated}
      />
    </div>
  );
}
