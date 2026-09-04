"use client";

import React, { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Bell, Clock, Radio, ShieldCheck } from "lucide-react";

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Command Center Dashboard",
    subtitle: "Real-time heavy mining proximity monitoring & safety metrics",
  },
  "/monitoring": {
    title: "Live Camera Feeds & AI Telemetry",
    subtitle: "Multi-angle YOLOv8 detection, ByteTrack vectors, and spatial radar",
  },
  "/incidents": {
    title: "Safety Incident Logs & Replays",
    subtitle: "Proximity violations, closing velocities, and 5-second R2 video archives",
  },
  "/workers": {
    title: "Personnel & Biometric Registry",
    subtitle: "DeepFace Facenet512 profiles, authorization status, and supervision hierarchy",
  },
  "/machines": {
    title: "Heavy Equipment Fleet",
    subtitle: "Haul trucks, hydraulic excavators, wheel loaders, and telemetry sensors",
  },
  "/settings": {
    title: "System Configuration & Thresholds",
    subtitle: "Spatial safety zones, debounce windows, Cloudflare R2, and Resend alerts",
  },
};

export default function Header(): React.JSX.Element {
  const pathname = usePathname();
  const [timeString, setTimeString] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeString(
        now.toISOString().replace("T", " ").substring(0, 19) + " UTC"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const routeInfo = routeTitles[pathname] || {
    title: "HALOCAS Operations",
    subtitle: "Mining Safety Platform",
  };

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-6 py-4 bg-[#111827]/90 backdrop-blur-md border-b border-[#374151]">
      <div className="flex flex-col pl-10 lg:pl-0">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          {routeInfo.title}
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">{routeInfo.subtitle}</p>
      </div>

      <div className="flex items-center space-x-4">
        {/* Real-time Clock */}
        <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#1f2937] border border-[#374151] text-xs font-mono text-gray-300">
          <Clock className="w-3.5 h-3.5 text-[#00FFFF]" />
          <span>{timeString || "2026-09-04 20:25:00 UTC"}</span>
        </div>

        {/* Live Status Badge */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#1f2937] border border-[#10B981]/40 text-xs font-mono text-[#10B981]">
          <Radio className="w-3.5 h-3.5 animate-pulse text-[#10B981]" />
          <span className="hidden md:inline font-bold">RADAR ACTIVE</span>
        </div>

        {/* Safety Status Pill */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#1f2937] border border-[#374151] text-xs text-gray-300">
          <ShieldCheck className="w-4 h-4 text-[#00FFFF]" />
          <span className="hidden lg:inline text-xs font-medium">Zone A Normal</span>
        </div>

        {/* Notifications Icon Button */}
        <button
          className="relative p-2 rounded-lg bg-[#1f2937] border border-[#374151] text-gray-300 hover:text-white hover:border-[#00FFFF]/40 transition-colors"
          aria-label="Alerts"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#FF3B30] animate-ping" />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#FF3B30]" />
        </button>
      </div>
    </header>
  );
}
