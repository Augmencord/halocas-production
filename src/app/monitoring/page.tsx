"use client";

import React, { useState } from "react";
import {
  Radio,
  Camera,
  Maximize2,
  Play,
  Pause,
  HardHat,
  Truck,
  Shield,
} from "lucide-react";

interface CameraFeed {
  id: string;
  name: string;
  location: string;
  status: "ONLINE" | "STANDBY";
  fps: number;
  detectedCount: number;
}

const cameras: CameraFeed[] = [
  {
    id: "front",
    name: "Front Cabin Optical #1",
    location: "CAT-797F-01 (Haul Truck)",
    status: "ONLINE",
    fps: 29.8,
    detectedCount: 2,
  },
  {
    id: "rear",
    name: "Rear Blind-Spot Radar #2",
    location: "CAT-797F-01 (Haul Truck)",
    status: "ONLINE",
    fps: 30.0,
    detectedCount: 0,
  },
  {
    id: "excavator_boom",
    name: "Boom Panoramic #3",
    location: "HITACHI-EX8000-02 (Excavator)",
    status: "ONLINE",
    fps: 29.5,
    detectedCount: 1,
  },
  {
    id: "pit_overview",
    name: "Perimeter High-Mast #4",
    location: "Sector 04 Central Mast",
    status: "ONLINE",
    fps: 25.0,
    detectedCount: 4,
  },
];

export default function LiveMonitoringPage(): React.JSX.Element {
  const [selectedCam, setSelectedCam] = useState<string>("front");
  const [isPaused, setIsPaused] = useState<boolean>(false);

  const activeCam =
    cameras.find((c) => c.id === selectedCam) || cameras[0];

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/30 text-[#00FFFF]">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>{activeCam.name}</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                {activeCam.status}
              </span>
            </h2>
            <p className="text-xs text-gray-400">{activeCam.location}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/40 text-gray-300 hover:text-white transition-all"
          >
            {isPaused ? (
              <>
                <Play className="w-3.5 h-3.5 text-[#10B981]" />
                <span>Resume Feed</span>
              </>
            ) : (
              <>
                <Pause className="w-3.5 h-3.5 text-[#F59E0B]" />
                <span>Freeze Frame</span>
              </>
            )}
          </button>
          <div className="px-3 py-1.5 rounded-lg bg-[#111827] border border-[#374151] text-gray-300">
            FPS: <span className="text-[#00FFFF] font-bold">{activeCam.fps}</span>
          </div>
        </div>
      </div>

      {/* Main Viewport & Camera Selector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left 3 Cols: Primary Live Video Viewport */}
        <div className="lg:col-span-3 space-y-4">
          <div className="relative aspect-video w-full rounded-2xl bg-[#0B0F17] border border-[#374151] overflow-hidden flex flex-col justify-between p-4 shadow-2xl hud-grid">
            {/* Top Telemetry Overlay */}
            <div className="flex items-center justify-between z-10 font-mono text-[11px] text-white">
              <div className="flex items-center gap-3 bg-[#111827]/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-[#374151]">
                <span className="flex items-center gap-1.5 text-[#FF3B30] font-bold">
                  <span className="w-2 h-2 rounded-full bg-[#FF3B30] animate-ping" />
                  REC [60s RING]
                </span>
                <span className="text-gray-400">|</span>
                <span>CAM: {activeCam.id.toUpperCase()}</span>
                <span className="text-gray-400">|</span>
                <span>RES: 1920x1080</span>
              </div>

              <div className="flex items-center gap-2 bg-[#111827]/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-[#374151]">
                <Shield className="w-3.5 h-3.5 text-[#00FFFF]" />
                <span>HALO RADIUS: 10.0m</span>
              </div>
            </div>

            {/* Simulated Live Detection HUD Boxes */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              {/* Machine Detection Box */}
              <div className="absolute top-1/4 left-1/3 w-64 h-52 border-2 border-[#00FFFF]/80 bg-[#00FFFF]/5 rounded-md flex flex-col justify-between p-1.5">
                <div className="self-start px-1.5 py-0.5 rounded bg-[#00FFFF] text-[#111827] text-[10px] font-mono font-bold flex items-center gap-1">
                  <Truck className="w-3 h-3" />
                  <span>TRUCK #1 (94.2%)</span>
                </div>
                <div className="self-end text-[10px] font-mono text-[#00FFFF] bg-[#111827]/90 px-1 rounded">
                  v = 4.2 m/s
                </div>
              </div>

              {/* Worker Detection Box (Proximity Warning) */}
              <div className="absolute top-1/3 right-1/4 w-28 h-44 border-2 border-[#F59E0B] bg-[#F59E0B]/10 rounded-md flex flex-col justify-between p-1.5 animate-pulse">
                <div className="self-start px-1.5 py-0.5 rounded bg-[#F59E0B] text-[#111827] text-[10px] font-mono font-bold flex items-center gap-1">
                  <HardHat className="w-3 h-3" />
                  <span>WORKER (91%)</span>
                </div>
                <div className="self-center bg-[#111827]/90 text-[#F59E0B] border border-[#F59E0B]/40 px-1 py-0.5 rounded text-[9px] font-mono font-bold">
                  DIST: 6.8m (WARN)
                </div>
                <div className="self-end text-[9px] font-mono text-gray-300 bg-[#111827]/90 px-1 rounded">
                  M. Vance
                </div>
              </div>
            </div>

            {/* Bottom Controls Overlay */}
            <div className="flex items-center justify-between z-10 font-mono text-[11px] text-gray-400">
              <div className="bg-[#111827]/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-[#374151]">
                MODEL: YOLOv8n-pose | BYTE-TRACK ID #42
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="p-1.5 rounded-lg bg-[#111827]/80 hover:bg-[#1f2937] border border-[#374151] text-gray-300 hover:text-[#00FFFF] transition-colors"
                  title="Full Screen"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Quick Diagnostics */}
          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xl bg-[#1f2937] border border-[#374151]">
              <span className="text-gray-400 block text-[10px]">BUFFER RETENTION</span>
              <span className="text-white font-bold">1,800 Frames (60.0s)</span>
            </div>
            <div className="p-3 rounded-xl bg-[#1f2937] border border-[#374151]">
              <span className="text-gray-400 block text-[10px]">EXPORT CODEC</span>
              <span className="text-[#00FFFF] font-bold">mp4v (Fallback: avc1)</span>
            </div>
            <div className="p-3 rounded-xl bg-[#1f2937] border border-[#374151]">
              <span className="text-gray-400 block text-[10px]">CALIBRATION</span>
              <span className="text-[#10B981] font-bold">20.0 px/m (Fixed)</span>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Camera Switcher */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
            <Camera className="w-4 h-4 text-[#00FFFF]" />
            Multi-Camera Selector
          </h3>

          <div className="space-y-2.5">
            {cameras.map((cam) => {
              const isSelected = cam.id === selectedCam;
              return (
                <button
                  key={cam.id}
                  onClick={() => setSelectedCam(cam.id)}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                    isSelected
                      ? "bg-[#1f2937] border-[#00FFFF] shadow-[0_0_12px_rgba(0,255,255,0.15)]"
                      : "bg-[#1f2937]/60 border-[#374151] hover:border-gray-500 hover:bg-[#1f2937]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">
                      {cam.name}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                      {cam.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-400 mt-1">{cam.location}</p>
                  <div className="flex items-center justify-between text-[10px] font-mono text-gray-400 mt-2 pt-2 border-t border-[#374151]/50">
                    <span>{cam.fps} FPS</span>
                    <span>{cam.detectedCount} Targets Active</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
