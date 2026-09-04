"use client";

import React, { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Activity, Clock, ShieldAlert } from "lucide-react";
import { HourlyIncidentPoint, generate24HourTimeline } from "../../lib/api";

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-3 rounded-xl bg-[#111827]/95 border border-[#374151] backdrop-blur-md shadow-xl text-xs font-mono">
        <div className="text-gray-400 font-bold mb-1.5 flex items-center gap-1">
          <Clock className="w-3 h-3 text-[#00FFFF]" />
          <span>TIME: {label}</span>
        </div>
        <div className="space-y-1">
          {payload.map((entry, index) => (
            <div
              key={`item-${index}`}
              className="flex items-center justify-between gap-4"
            >
              <span className="flex items-center gap-1.5" style={{ color: entry.color }}>
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                {entry.name}:
              </span>
              <span className="font-bold text-white">{entry.value} events</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export default function IncidentChart(): React.JSX.Element {
  const [data, setData] = useState<HourlyIncidentPoint[]>(() => generate24HourTimeline());
  const [isMounted, setIsMounted] = useState<boolean>(false);
  const [activeRange, setActiveRange] = useState<"24h" | "shift">("24h");

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsMounted(true);
    }, 0);

    // Update hourly points every 60s
    const interval = setInterval(() => {
      setData(generate24HourTimeline());
    }, 60000);

    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, []);

  const chartData = activeRange === "shift" ? data.slice(-8) : data;

  return (
    <div className="flex flex-col justify-between rounded-2xl bg-[#1f2937]/90 backdrop-blur-md border border-[#374151] p-5 shadow-2xl overflow-hidden">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#374151]/70">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/30 text-[#00FFFF]">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
              <span>REAL-TIME INCIDENT FREQUENCY</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#00FFFF]/15 text-[#00FFFF] border border-[#00FFFF]/30">
                RECHARTS
              </span>
            </h3>
            <p className="text-[11px] text-gray-400 font-mono">
              TEMPORAL PROXIMITY EVENT DENSITY
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center bg-[#111827] p-1 rounded-xl border border-[#374151]">
            <button
              onClick={() => setActiveRange("24h")}
              className={`px-3 py-1 text-xs font-mono font-bold rounded-lg transition-all ${
                activeRange === "24h"
                  ? "bg-[#00FFFF] text-[#111827] shadow-cyan-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              LAST 24 HOURS
            </button>
            <button
              onClick={() => setActiveRange("shift")}
              className={`px-3 py-1 text-xs font-mono font-bold rounded-lg transition-all ${
                activeRange === "shift"
                  ? "bg-[#00FFFF] text-[#111827] shadow-cyan-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              CURRENT SHIFT (8H)
            </button>
          </div>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="my-3 h-64 w-full">
        {isMounted ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <defs>
                {/* Cyan Gradient for Warnings */}
                <linearGradient id="warningGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00FFFF" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#00FFFF" stopOpacity={0.0} />
                </linearGradient>
                {/* Red Gradient for Critical Breaches */}
                <linearGradient id="criticalGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF3B30" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#FF3B30" stopOpacity={0.0} />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(55, 65, 81, 0.4)"
                vertical={false}
              />
              <XAxis
                dataKey="hour"
                stroke="#6B7280"
                fontSize={10}
                tickLine={false}
                fontFamily="monospace"
              />
              <YAxis
                stroke="#6B7280"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                fontFamily="monospace"
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                align="right"
                iconType="circle"
                wrapperStyle={{
                  paddingBottom: "10px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                }}
              />

              <Area
                type="monotone"
                dataKey="warning"
                name="Warning Zone (<10m)"
                stroke="#00FFFF"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#warningGradient)"
              />
              <Area
                type="monotone"
                dataKey="critical"
                name="Critical Breach (<3m)"
                stroke="#FF3B30"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#criticalGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-[#111827]/40 rounded-xl border border-[#374151] animate-pulse text-xs font-mono text-gray-500">
            LOADING TEMPORAL TELEMETRY...
          </div>
        )}
      </div>

      {/* Footer Metrics */}
      <div className="pt-2 border-t border-[#374151]/50 flex items-center justify-between text-xs font-mono text-gray-400">
        <span className="flex items-center gap-1.5 text-gray-300">
          <ShieldAlert className="w-3.5 h-3.5 text-[#FF3B30]" />
          Shift Peak: 15:00 UTC (Shift Changeover)
        </span>
        <span className="text-[11px] text-[#10B981]">
          Trend: Normal Velocity Distribution
        </span>
      </div>
    </div>
  );
}
