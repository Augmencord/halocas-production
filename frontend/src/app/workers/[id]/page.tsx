"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  HardHat,
  Fingerprint,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Mail,
  Building,
  Calendar,
  Camera,
  Play,
  CheckCircle2,
  X,
  UploadCloud,
  Loader2,
  TrendingDown,
  Activity,
  AlertCircle,
  Video,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  fetchWorkerById,
  updateWorkerAuthorization,
  enrollWorkerFace,
  generateWorkerIncidentFrequency,
  WorkerDetail,
  IncidentItem,
  WorkerAlertPoint,
} from "@/lib/api";
import { VideoPlayer } from "@/components/VideoPlayer";

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
}

const AlertTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-3 rounded-xl bg-[#111827]/95 border border-[#374151] backdrop-blur-md shadow-xl text-xs font-mono">
        <div className="text-gray-400 font-bold mb-1.5 flex items-center gap-1">
          <Calendar className="w-3 h-3 text-[#00FFFF]" />
          <span>MONTH: {label}</span>
        </div>
        <div className="space-y-1">
          {payload.map((entry, index) => (
            <div
              key={`item-${index}`}
              className="flex items-center justify-between gap-4"
            >
              <span
                className="flex items-center gap-1.5"
                style={{ color: entry.color }}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                {entry.name}:
              </span>
              <span className="font-bold text-white">{entry.value} alerts</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export default function WorkerDetailPage(): React.JSX.Element {
  const params = useParams();
  const rawId = params?.id;
  const workerId = Number(rawId) || 1001;

  const [worker, setWorker] = useState<WorkerDetail | null>(null);
  const [chartData, setChartData] = useState<WorkerAlertPoint[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState<boolean>(false);

  // Authorization toggle state
  const [isUpdatingAuth, setIsUpdatingAuth] = useState<boolean>(false);

  // Video modal state
  const [activeClip, setActiveClip] = useState<IncidentItem | null>(null);

  // Re-enroll modal state
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState<boolean>(false);
  const [enrollFile, setEnrollFile] = useState<File | null>(null);
  const [enrollPreview, setEnrollPreview] = useState<string | null>(null);
  const [isEnrolling, setIsEnrolling] = useState<boolean>(false);
  const [enrollError, setEnrollError] = useState<string | null>(null);
  const [enrollSuccessMsg, setEnrollSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const run = async (): Promise<void> => {
      try {
        const data = await fetchWorkerById(workerId);
        if (active) {
          setWorker(data);
          setChartData(generateWorkerIncidentFrequency(workerId));
          setError(null);
          setIsLoading(false);
          setIsMounted(true);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Failed to load worker profile."
          );
          setIsLoading(false);
          setIsMounted(true);
        }
      }
    };

    void run();

    return () => {
      active = false;
    };
  }, [workerId]);

  const handleRetry = (): void => {
    setIsLoading(true);
    setError(null);
    void fetchWorkerById(workerId)
      .then((data) => {
        setWorker(data);
        setChartData(generateWorkerIncidentFrequency(workerId));
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Failed to load worker profile."
        );
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  // Handle Authorization Toggle
  const handleToggleAuthorization = async (): Promise<void> => {
    if (!worker) return;
    const newStatus = !worker.is_authorized;
    setIsUpdatingAuth(true);

    // Optimistic UI update
    setWorker((prev) => (prev ? { ...prev, is_authorized: newStatus } : null));

    try {
      await updateWorkerAuthorization(worker.id, newStatus);
    } catch {
      // Revert if failed
      setWorker((prev) =>
        prev ? { ...prev, is_authorized: !newStatus } : null
      );
    } finally {
      setIsUpdatingAuth(false);
    }
  };

  // Handle Face Re-enrollment
  const handleEnrollFaceSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!enrollFile || !worker) return;

    setIsEnrolling(true);
    setEnrollError(null);
    try {
      const res = await enrollWorkerFace(worker.id, enrollFile);
      setEnrollSuccessMsg(res.message);
      setWorker((prev) =>
        prev
          ? {
              ...prev,
              has_face_embedding: true,
              face_photo_url: res.photoUrl,
            }
          : null
      );
      setTimeout(() => {
        setIsEnrollModalOpen(false);
        setEnrollSuccessMsg(null);
        setEnrollFile(null);
        setEnrollPreview(null);
      }, 1500);
    } catch (err) {
      setEnrollError(
        err instanceof Error ? err.message : "Failed to enroll face portrait."
      );
    } finally {
      setIsEnrolling(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 pb-12">
        <div className="h-6 w-32 bg-gray-800 rounded animate-pulse" />
        <div className="p-8 rounded-3xl bg-[#1f2937]/70 border border-[#374151] animate-pulse h-64" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64 rounded-3xl bg-[#1f2937]/70 border border-[#374151] animate-pulse" />
          <div className="h-64 rounded-3xl bg-[#1f2937]/70 border border-[#374151] animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !worker) {
    return (
      <div className="space-y-6 pb-12">
        <Link
          href="/workers"
          className="inline-flex items-center gap-2 text-xs font-mono text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Personnel Directory</span>
        </Link>
        <div className="p-8 rounded-3xl bg-[#FF3B30]/10 border border-[#FF3B30]/30 text-center space-y-4">
          <AlertCircle className="w-10 h-10 text-[#FF3B30] mx-auto" />
          <h2 className="text-lg font-bold text-white">Personnel Record Not Found</h2>
          <p className="text-xs text-gray-400">
            {error || `Worker with ID W-${workerId} could not be retrieved from the database.`}
          </p>
          <button
            onClick={handleRetry}
            className="px-4 py-2 rounded-xl bg-[#FF3B30]/20 hover:bg-[#FF3B30]/30 text-[#FF3B30] text-xs font-bold transition-colors"
          >
            Retry Fetch
          </button>
        </div>
      </div>
    );
  }

  const criticalIncidents = worker.recent_incidents.filter(
    (i) => i.severity === "CRITICAL"
  ).length;
  const warningIncidents = worker.recent_incidents.filter(
    (i) => i.severity === "WARNING"
  ).length;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Navigation & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/workers"
            className="p-2 rounded-xl bg-[#1f2937] border border-[#374151] text-gray-400 hover:text-white hover:border-[#00FFFF] transition-colors"
            title="Return to Directory"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-gray-400">
              <Link href="/workers" className="hover:text-white transition-colors">
                Personnel
              </Link>
              <span>/</span>
              <span className="text-white font-bold">W-{worker.id}</span>
            </div>
            <h1 className="text-xl font-black text-white tracking-tight">
              {worker.name}
            </h1>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2.5">
          {/* Re-enroll Face Button */}
          <button
            onClick={() => setIsEnrollModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#1f2937] border border-[#374151] hover:border-[#00FFFF] text-gray-200 hover:text-white text-xs font-semibold transition-colors"
          >
            <Camera className="w-3.5 h-3.5 text-[#00FFFF]" />
            <span>Update Biometrics</span>
          </button>

          {/* Authorization Toggle */}
          <button
            onClick={handleToggleAuthorization}
            disabled={isUpdatingAuth}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              worker.is_authorized
                ? "bg-[#00FFFF]/20 border border-[#00FFFF] text-[#00FFFF] hover:bg-[#00FFFF]/30"
                : "bg-gray-800 border border-gray-700 text-gray-300 hover:text-white"
            }`}
          >
            {isUpdatingAuth ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : worker.is_authorized ? (
              <ShieldCheck className="w-3.5 h-3.5 text-[#00FFFF]" />
            ) : (
              <ShieldAlert className="w-3.5 h-3.5 text-[#F59E0B]" />
            )}
            <span>
              {worker.is_authorized ? "Zone Authorized" : "Zone Restricted"}
            </span>
          </button>
        </div>
      </div>

      {/* Hero Profile Dossier Card */}
      <div className="p-6 rounded-3xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-md shadow-xl flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
          {/* Large Worker Portrait with Biometric Frame */}
          <div className="relative w-24 h-24 rounded-2xl bg-[#111827] border-2 border-[#374151] overflow-hidden flex items-center justify-center shrink-0 shadow-inner">
            {worker.face_photo_url ? (
              <Image
                src={worker.face_photo_url}
                alt={worker.name}
                width={96}
                height={96}
                className="w-full h-full object-cover"
                unoptimized
              />
            ) : (
              <div className="text-gray-400 font-bold font-mono text-2xl">
                {worker.name
                  .split(" ")
                  .map((n) => n[0])
                  .join("")}
              </div>
            )}

            {/* Corner Reticle Brackets */}
            <div className="absolute top-1 left-1 w-2 h-2 border-t-2 border-l-2 border-[#00FFFF]" />
            <div className="absolute top-1 right-1 w-2 h-2 border-t-2 border-r-2 border-[#00FFFF]" />
            <div className="absolute bottom-1 left-1 w-2 h-2 border-b-2 border-l-2 border-[#00FFFF]" />
            <div className="absolute bottom-1 right-1 w-2 h-2 border-b-2 border-r-2 border-[#00FFFF]" />
          </div>

          {/* Details & Roles */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-black text-white">{worker.name}</h2>
              <span className="px-2.5 py-0.5 rounded-lg bg-[#111827] border border-[#374151] text-xs font-mono text-gray-300">
                W-{worker.id}
              </span>
              {worker.is_authorized ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#00FFFF]/15 text-[#00FFFF] border border-[#00FFFF]/30">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  HEAVY MACHINERY CLEARANCE
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  RESTRICTED SAFETY HALO
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-400">
              <div className="flex items-center gap-1.5">
                <HardHat className="w-3.5 h-3.5 text-[#00FFFF]" />
                <span className="text-gray-300 font-medium">{worker.role}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-[#00FFFF]" />
                <span>Department: {worker.department}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-[#00FFFF]" />
                <span>
                  Supervisor:{" "}
                  {worker.supervisor_email ? (
                    <a
                      href={`mailto:${worker.supervisor_email}`}
                      className="text-[#00FFFF] underline underline-offset-2"
                    >
                      {worker.supervisor_email}
                    </a>
                  ) : (
                    "Not assigned"
                  )}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-[#00FFFF]" />
                <span>
                  Registered:{" "}
                  {new Date(worker.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Biometrics Status Dossier Pill */}
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#374151] space-y-2 min-w-[240px]">
          <div className="text-xs font-bold text-gray-300 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Fingerprint className="w-4 h-4 text-[#10B981]" />
              DeepFace Biometrics
            </span>
            <span className="text-[10px] text-gray-500 font-mono">Facenet512</span>
          </div>

          <div className="space-y-1 text-xs font-mono">
            <div className="flex justify-between text-gray-400">
              <span>Embedding Vector:</span>
              <span className="text-white font-bold">
                {worker.has_face_embedding ? "512-D Computed" : "Pending"}
              </span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Cosine Threshold:</span>
              <span className="text-[#00FFFF]">0.65 Match</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>RetinaFace Detector:</span>
              <span className="text-[#10B981]">ONLINE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Row: 3 Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Infractions */}
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-400 font-mono uppercase">
            <span>Recorded Proximity Events</span>
            <AlertTriangle className="w-4 h-4 text-[#FF3B30]" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {worker.total_incidents}
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            {criticalIncidents} Critical · {warningIncidents} Warning
          </div>
        </div>

        {/* Compliance Rating */}
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-400 font-mono uppercase">
            <span>Safety Rating</span>
            <TrendingDown className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="text-2xl font-bold text-[#10B981] font-mono">
            {worker.total_incidents === 0
              ? "100% (Grade A)"
              : worker.total_incidents <= 2
              ? "92% (Grade B)"
              : "78% (Grade C)"}
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            Proximity compliance index
          </div>
        </div>

        {/* Active Zone Assignment */}
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-400 font-mono uppercase">
            <span>Zone Clearance</span>
            <Activity className="w-4 h-4 text-[#00FFFF]" />
          </div>
          <div className="text-2xl font-bold text-[#00FFFF] font-mono">
            {worker.is_authorized ? "Full Pit Access" : "Perimeter Only"}
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            Heavy machinery buffer: {worker.is_authorized ? "0.0m" : "3.0m"}
          </div>
        </div>
      </div>

      {/* Safety Alert Frequency Chart */}
      <div className="p-6 rounded-3xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-md shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#00FFFF]" />
              Proximity Alert Frequency (Last 6 Months)
            </h3>
            <p className="text-xs text-gray-400">
              Monthly distribution of critical vs warning proximity intrusions detected by camera buffers.
            </p>
          </div>
          <div className="text-xs font-mono text-gray-400">
            Total alerts:{" "}
            <span className="text-white font-bold">
              {chartData.reduce((acc, curr) => acc + curr.total, 0)}
            </span>
          </div>
        </div>

        <div className="h-64 w-full">
          {isMounted ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                <XAxis
                  dataKey="period"
                  stroke="#9CA3AF"
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis
                  stroke="#9CA3AF"
                  fontSize={11}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<AlertTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }}
                />
                <Bar
                  dataKey="critical"
                  name="Critical ( <3.0m )"
                  fill="#FF3B30"
                  radius={[4, 4, 0, 0]}
                  stackId="alerts"
                />
                <Bar
                  dataKey="warning"
                  name="Warning ( 3.0m - 10.0m )"
                  fill="#F59E0B"
                  radius={[4, 4, 0, 0]}
                  stackId="alerts"
                />
                <Bar
                  dataKey="caution"
                  name="Caution ( Advisory )"
                  fill="#00FFFF"
                  radius={[4, 4, 0, 0]}
                  stackId="alerts"
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-full bg-[#111827]/40 rounded-2xl animate-pulse" />
          )}
        </div>
      </div>

      {/* Historical Incident Breaches Table */}
      <div className="p-6 rounded-3xl bg-[#1f2937]/90 border border-[#374151] backdrop-blur-md shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#FF3B30]" />
              Incident Breach History
            </h3>
            <p className="text-xs text-gray-400">
              Historical record of safety boundary compromises involving this worker.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-lg bg-[#111827] border border-[#374151] text-xs font-mono text-gray-300">
            {worker.recent_incidents.length} Records
          </span>
        </div>

        {worker.recent_incidents.length === 0 ? (
          <div className="p-8 rounded-2xl bg-[#111827]/50 border border-[#374151] text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-[#10B981] mx-auto" />
            <h4 className="text-sm font-bold text-white">Zero Incident Breaches</h4>
            <p className="text-xs text-gray-400 max-w-sm mx-auto">
              This worker has maintained an unblemished record with zero safety perimeter intrusions.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#374151] text-gray-400 font-mono uppercase text-[10px]">
                  <th className="pb-3 font-semibold">Incident ID</th>
                  <th className="pb-3 font-semibold">Timestamp</th>
                  <th className="pb-3 font-semibold">Machinery Involved</th>
                  <th className="pb-3 font-semibold">Monocular Distance</th>
                  <th className="pb-3 font-semibold">Severity</th>
                  <th className="pb-3 font-semibold">Closing Velocity</th>
                  <th className="pb-3 font-semibold">Supervisor Alert</th>
                  <th className="pb-3 font-semibold text-right">Playback</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#374151]/50">
                {worker.recent_incidents.map((inc) => (
                  <tr
                    key={inc.id}
                    className="hover:bg-[#111827]/40 transition-colors"
                  >
                    <td className="py-3 font-mono font-bold text-[#00FFFF]">
                      #{inc.id}
                    </td>
                    <td className="py-3 text-gray-300 font-mono">
                      {new Date(inc.timestamp).toLocaleString("en-US", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="py-3 text-white font-medium">
                      CAT-797F-0{inc.machine_id}
                    </td>
                    <td className="py-3 font-mono">
                      <span
                        className={`font-bold ${
                          inc.distance_meters <= 3.0
                            ? "text-[#FF3B30]"
                            : "text-[#F59E0B]"
                        }`}
                      >
                        {inc.distance_meters.toFixed(1)}m
                      </span>
                    </td>
                    <td className="py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                          inc.severity === "CRITICAL"
                            ? "bg-[#FF3B30]/15 text-[#FF3B30] border-[#FF3B30]/30"
                            : "bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30"
                        }`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-3 text-gray-300 font-mono">
                      {inc.closing_velocity
                        ? `${inc.closing_velocity.toFixed(1)} m/s`
                        : "Stationary"}
                    </td>
                    <td className="py-3 font-mono text-[11px]">
                      {inc.supervisor_notified ? (
                        <span className="text-[#10B981] flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Dispatched
                        </span>
                      ) : (
                        <span className="text-gray-500">Suppressed</span>
                      )}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => setActiveClip(inc)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF] text-gray-300 hover:text-[#00FFFF] text-xs font-semibold transition-colors"
                      >
                        <Play className="w-3 h-3" />
                        <span>Clip</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Video Clip Modal */}
      {activeClip && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl rounded-3xl bg-[#1f2937] border border-[#374151] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#374151]">
              <div className="flex items-center gap-2">
                <Video className="w-5 h-5 text-[#00FFFF]" />
                <h4 className="text-base font-bold text-white">
                  Incident #{activeClip.id} Clip Playback
                </h4>
              </div>
              <button
                onClick={() => setActiveClip(null)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <VideoPlayer
              src={activeClip.clip_url}
              incidentId={activeClip.id}
              title={`INCIDENT #${activeClip.id} - CAT-797F-0${activeClip.machine_id}`}
              fps={30}
              autoPlay
              markers={[
                {
                  time: 1.5,
                  label: `Proximity Vector: ${activeClip.distance_meters.toFixed(1)}m`,
                  color: activeClip.severity === "CRITICAL" ? "red" : "amber",
                  description: `Severity: ${activeClip.severity} · Closing Velocity: ${
                    activeClip.closing_velocity
                      ? `${activeClip.closing_velocity.toFixed(1)} m/s`
                      : "Stationary"
                  }`,
                },
              ]}
            />
          </div>
        </div>
      )}

      {/* Face Biometrics Re-enroll Modal */}
      {isEnrollModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-md rounded-3xl bg-[#1f2937] border border-[#374151] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#374151]">
              <div className="flex items-center gap-2">
                <Camera className="w-5 h-5 text-[#00FFFF]" />
                <h4 className="text-base font-bold text-white">
                  Update Biometric Face
                </h4>
              </div>
              <button
                onClick={() => setIsEnrollModalOpen(false)}
                disabled={isEnrolling}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {enrollError && (
              <div className="p-3 rounded-xl bg-[#FF3B30]/20 border border-[#FF3B30]/40 text-xs text-[#FF3B30]">
                {enrollError}
              </div>
            )}

            {enrollSuccessMsg && (
              <div className="p-3 rounded-xl bg-[#10B981]/20 border border-[#10B981]/40 text-xs text-[#10B981] flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>{enrollSuccessMsg}</span>
              </div>
            )}

            <form onSubmit={handleEnrollFaceSubmit} className="space-y-4">
              <p className="text-xs text-gray-400">
                Upload an updated frontal portrait for <strong>{worker.name}</strong>. DeepFace RetinaFace will compute an updated 512-D normalized embedding vector.
              </p>

              {enrollPreview ? (
                <div className="relative w-32 h-32 mx-auto rounded-2xl overflow-hidden border-2 border-[#00FFFF] bg-black">
                  <Image
                    src={enrollPreview}
                    alt="New portrait"
                    width={128}
                    height={128}
                    className="w-full h-full object-cover"
                    unoptimized
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setEnrollFile(null);
                      setEnrollPreview(null);
                    }}
                    className="absolute top-1 right-1 p-1 rounded-full bg-black/70 text-white hover:bg-black"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <label className="border-2 border-dashed border-[#374151] hover:border-[#00FFFF] rounded-2xl p-6 text-center block cursor-pointer bg-[#111827]/50 transition-colors">
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        const file = e.target.files[0];
                        setEnrollFile(file);
                        setEnrollPreview(URL.createObjectURL(file));
                      }
                    }}
                  />
                  <UploadCloud className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <div className="text-xs font-semibold text-white">
                    Click to select frontal portrait
                  </div>
                  <div className="text-[10px] text-gray-500 mt-1">
                    JPG, PNG, WEBP (Min 200x200)
                  </div>
                </label>
              )}

              <div className="flex justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEnrollModalOpen(false)}
                  disabled={isEnrolling}
                  className="px-4 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs font-semibold text-gray-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!enrollFile || isEnrolling}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {isEnrolling ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Extracting 512-D...</span>
                    </>
                  ) : (
                    <span>Compute & Save Vector</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
