"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  fetchIncidents,
  notifySupervisor,
  IncidentItem,
  IncidentFilterParams,
} from "../../lib/api";
import IncidentFilters from "../../components/incidents/IncidentFilters";
import IncidentTable, {
  SortField,
  SortDirection,
} from "../../components/incidents/IncidentTable";
import IncidentDetailModal from "../../components/incidents/IncidentDetailModal";
import { CheckCircle2, AlertCircle } from "lucide-react";

export default function IncidentsPage(): React.JSX.Element {
  const [filters, setFilters] = useState<IncidentFilterParams>({
    date_range: "all",
    severity: undefined,
    worker_search: "",
    machine_id: undefined,
    zone: undefined,
    offset: 0,
    limit: 10,
  });

  const [incidents, setIncidents] = useState<IncidentItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sorting state
  const [sortField, setSortField] = useState<SortField>("timestamp");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Detail Modal selection
  const [selectedIncident, setSelectedIncident] = useState<IncidentItem | null>(
    null
  );

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const executeFetch = useCallback(async () => {
    try {
      const { incidents: data, totalCount: count } = await fetchIncidents(filters);

      const sorted = [...data].sort((a, b) => {
        let comp = 0;
        if (sortField === "timestamp") {
          comp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        } else if (sortField === "severity") {
          const rank = { CRITICAL: 3, WARNING: 2, CAUTION: 1 };
          comp = rank[a.severity] - rank[b.severity];
        } else if (sortField === "distance_meters") {
          comp = a.distance_meters - b.distance_meters;
        } else if (sortField === "closing_velocity") {
          comp = (a.closing_velocity || 0) - (b.closing_velocity || 0);
        } else if (sortField === "worker_name") {
          comp = (a.worker_name || "").localeCompare(b.worker_name || "");
        }
        return sortDirection === "asc" ? comp : -comp;
      });

      setIncidents(sorted);
      setTotalCount(count);
      setErrorMsg(null);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load incidents");
    } finally {
      setIsLoading(false);
    }
  }, [filters, sortField, sortDirection]);

  useEffect(() => {
    let active = true;

    const run = async () => {
      try {
        const { incidents: data, totalCount: count } = await fetchIncidents(filters);
        if (active) {
          const sorted = [...data].sort((a, b) => {
            let comp = 0;
            if (sortField === "timestamp") {
              comp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
            } else if (sortField === "severity") {
              const rank = { CRITICAL: 3, WARNING: 2, CAUTION: 1 };
              comp = rank[a.severity] - rank[b.severity];
            } else if (sortField === "distance_meters") {
              comp = a.distance_meters - b.distance_meters;
            } else if (sortField === "closing_velocity") {
              comp = (a.closing_velocity || 0) - (b.closing_velocity || 0);
            } else if (sortField === "worker_name") {
              comp = (a.worker_name || "").localeCompare(b.worker_name || "");
            }
            return sortDirection === "asc" ? comp : -comp;
          });

          setIncidents(sorted);
          setTotalCount(count);
          setErrorMsg(null);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (active) {
          setErrorMsg(err instanceof Error ? err.message : "Failed to load incidents");
          setIsLoading(false);
        }
      }
    };

    void run();

    return () => {
      active = false;
    };
  }, [filters, sortField, sortDirection]);

  const handleFilterChange = (newFilters: Partial<IncidentFilterParams>) => {
    setIsLoading(true);
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      offset: 0,
    }));
  };

  const handleResetFilters = () => {
    setIsLoading(true);
    setFilters({
      date_range: "all",
      severity: undefined,
      worker_search: "",
      machine_id: undefined,
      zone: undefined,
      start_date: undefined,
      end_date: undefined,
      offset: 0,
      limit: filters.limit || 10,
    });
    showToast("Filters reset to default view.");
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const handlePageChange = (newPage: number) => {
    setIsLoading(true);
    const limit = filters.limit || 10;
    const newOffset = (newPage - 1) * limit;
    setFilters((prev) => ({ ...prev, offset: newOffset }));
  };

  const handlePageSizeChange = (newSize: number) => {
    setIsLoading(true);
    setFilters((prev) => ({ ...prev, limit: newSize, offset: 0 }));
  };

  const handleNotifySupervisor = async (incidentId: number) => {
    const res = await notifySupervisor(incidentId);
    showToast(res.message);
  };

  const handleExportCSV = () => {
    if (incidents.length === 0) {
      showToast("No records available to export.");
      return;
    }

    const headers = [
      "Incident ID",
      "Timestamp UTC",
      "Worker ID",
      "Worker Name",
      "Machine ID",
      "Distance (m)",
      "Severity",
      "Closing Velocity (m/s)",
      "Supervisor Email",
      "Supervisor Notified",
      "Zone",
      "Clip URL",
    ];

    const rows = incidents.map((inc) => [
      `INC-${inc.id}`,
      inc.timestamp,
      inc.worker_id ?? "",
      `"${(inc.worker_name ?? "Unidentified").replace(/"/g, '""')}"`,
      `CAT-797F-0${inc.machine_id}`,
      inc.distance_meters.toFixed(1),
      inc.severity,
      inc.closing_velocity ? inc.closing_velocity.toFixed(1) : "",
      inc.supervisor_email ?? "",
      inc.supervisor_notified ? "TRUE" : "FALSE",
      `"${(inc.zone ?? "").replace(/"/g, '""')}"`,
      inc.clip_url ?? "",
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    link.setAttribute("download", `halocas_incidents_${dateStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    showToast(`Downloaded CSV archive with ${incidents.length} incident records.`);
  };

  const currentPage = Math.floor((filters.offset || 0) / (filters.limit || 10)) + 1;
  const pageSize = filters.limit || 10;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-[#1f2937] via-[#1f2937]/95 to-[#111827] border border-[#374151] relative overflow-hidden shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30">
              ● INCIDENT AUDIT REPOSITORY
            </span>
            <span className="text-xs text-gray-400 font-mono">
              HALO VISION &amp; BIOMETRIC FORENSICS
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            Proximity Violations &amp; Replay Archives
          </h2>
          <p className="text-xs text-gray-400">
            Audit trailing, video evidence retrieval, closing velocities, and supervisor email dispatch records.
          </p>
        </div>

        {/* Global Toast Notification */}
        {toastMessage && (
          <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#10B981]/20 border border-[#10B981]/40 text-xs font-mono font-bold text-[#10B981] animate-fade-in shadow-lg">
            <CheckCircle2 className="w-4 h-4" />
            <span>{toastMessage}</span>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-[#FF3B30]/10 border border-[#FF3B30]/30 text-xs font-mono text-[#FF3B30] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[#FF3B30]" />
            <span>API notification: {errorMsg} (Displaying offline records)</span>
          </div>
          <button
            onClick={() => {
              setIsLoading(true);
              void executeFetch();
            }}
            className="underline hover:text-white"
          >
            Retry
          </button>
        </div>
      )}

      {/* 1. Filters Bar */}
      <IncidentFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
        onExportCSV={handleExportCSV}
        totalFiltered={totalCount}
      />

      {/* 2. Incidents Table */}
      <IncidentTable
        incidents={incidents}
        totalCount={totalCount}
        currentPage={currentPage}
        pageSize={pageSize}
        sortField={sortField}
        sortDirection={sortDirection}
        onSort={handleSort}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
        onSelectIncident={(inc) => setSelectedIncident(inc)}
        onNotifySupervisor={handleNotifySupervisor}
        isLoading={isLoading}
      />

      {/* 3. Incident Detail Modal */}
      <IncidentDetailModal
        incident={selectedIncident}
        onClose={() => setSelectedIncident(null)}
        onNotifySupervisor={handleNotifySupervisor}
      />
    </div>
  );
}
