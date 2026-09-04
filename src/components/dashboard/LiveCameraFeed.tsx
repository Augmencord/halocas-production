"use client";

import React, { useState, useRef } from "react";
import {
  Camera,
  Maximize2,
  Minimize2,
  Radio,
  ShieldAlert,
  HardHat,
  Truck,
  RotateCw,
} from "lucide-react";

export default function LiveCameraFeed(): React.JSX.Element {
  const [cameraView, setCameraView] = useState<"front" | "rear">("front");
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [hasStreamError, setHasStreamError] = useState<boolean>(false);
  const [retryKey, setRetryKey] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const toggleFullscreen = async () => {
    if (!containerRef.current) return;

    if (!document.fullscreenElement) {
      try {
        await containerRef.current.requestFullscreen();
        setIsFullscreen(true);
      } catch {
        // Fullscreen not permitted or supported
      }
    } else {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  };

  const handleRetry = () => {
    setHasStreamError(false);
    setRetryKey((prev) => prev + 1);
  };

  const streamSrc = `/api/v1/stream/${cameraView}?t=${retryKey}`;

  return (
    <div
      ref={containerRef}
      className="relative flex flex-col justify-between rounded-2xl bg-[#1f2937]/90 backdrop-blur-md border border-[#374151] p-5 shadow-2xl overflow-hidden group"
    >
      {/* Top Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#374151]/70 z-10">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/30 text-[#00FFFF]">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
              <span>PRIMARY OPTICAL FEED</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                LIVE
              </span>
            </h3>
            <p className="text-[11px] text-gray-400 font-mono">
              MOUNTED ON: CAT-797F-01 (ULTRA-HAUL)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Front / Rear Camera Angle Switcher */}
          <div className="flex items-center bg-[#111827] p-1 rounded-xl border border-[#374151]">
            <button
              onClick={() => {
                setCameraView("front");
                setHasStreamError(false);
              }}
              className={`px-3 py-1 text-xs font-mono font-bold rounded-lg transition-all ${
                cameraView === "front"
                  ? "bg-[#00FFFF] text-[#111827] shadow-cyan-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              FRONT
            </button>
            <button
              onClick={() => {
                setCameraView("rear");
                setHasStreamError(false);
              }}
              className={`px-3 py-1 text-xs font-mono font-bold rounded-lg transition-all ${
                cameraView === "rear"
                  ? "bg-[#00FFFF] text-[#111827] shadow-cyan-glow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              REAR
            </button>
          </div>

          {/* Fullscreen Button */}
          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-xl bg-[#111827] border border-[#374151] hover:border-[#00FFFF]/50 text-gray-300 hover:text-[#00FFFF] transition-all"
            title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Main Video Screen Area */}
      <div className="relative my-3 aspect-video w-full rounded-xl bg-[#0B0F17] border border-[#374151] overflow-hidden flex items-center justify-center hud-grid">
        {!hasStreamError ? (
          /* Live MJPEG Stream */
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={streamSrc}
            alt={`Live ${cameraView} Camera Stream`}
            onError={() => setHasStreamError(true)}
            className="w-full h-full object-cover"
          />
        ) : (
          /* High-fidelity Fallback Simulation HUD when dev camera hardware is offline */
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center space-y-3 bg-[#0B0F17]/95">
            {/* Simulated Bounding Boxes Overlay */}
            <div className="absolute top-1/4 left-1/4 w-44 h-36 border border-dashed border-[#00FFFF]/60 rounded p-1 flex flex-col justify-between pointer-events-none">
              <span className="text-[9px] font-mono text-[#00FFFF] bg-[#111827]/80 px-1 self-start">
                HAUL TRUCK (94%)
              </span>
              <span className="text-[8px] font-mono text-gray-400 self-end">
                v: 4.2 m/s
              </span>
            </div>

            <div className="absolute bottom-1/4 right-1/4 w-24 h-36 border border-[#FF3B30] bg-[#FF3B30]/10 rounded p-1 flex flex-col justify-between pointer-events-none animate-pulse">
              <span className="text-[9px] font-mono font-bold text-[#FF3B30] bg-[#111827] px-1 self-start">
                CRITICAL 2.3m
              </span>
              <span className="text-[8px] font-mono text-white self-center">
                M. Vance
              </span>
            </div>

            <div className="p-3 rounded-full bg-[#111827] border border-[#374151] text-gray-400">
              <Camera className="w-7 h-7 text-[#00FFFF]" />
            </div>
            <div>
              <div className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                {cameraView.toUpperCase()} CAMERA STREAM STANDBY
              </div>
              <p className="text-[11px] text-gray-400 max-w-sm mt-0.5">
                Connecting to <code>/api/v1/stream/{cameraView}</code>. Feed will stream automatically when camera buffer receives frames.
              </p>
            </div>
            <button
              onClick={handleRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1f2937] hover:bg-[#374151] text-xs font-mono text-[#00FFFF] border border-[#374151] hover:border-[#00FFFF]/40 transition-all"
            >
              <RotateCw className="w-3.5 h-3.5" />
              <span>Reconnect Stream</span>
            </button>
          </div>
        )}

        {/* Live HUD Overlay Elements */}
        <div className="absolute top-3 left-3 z-10 flex items-center gap-2 text-[10px] font-mono text-white bg-[#111827]/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-[#374151]">
          <span className="w-2 h-2 rounded-full bg-[#FF3B30] animate-ping" />
          <span className="font-bold text-[#FF3B30]">REC</span>
          <span className="text-gray-400">|</span>
          <span>FPS: 29.8</span>
          <span className="text-gray-400">|</span>
          <span>1080p</span>
        </div>

        <div className="absolute bottom-3 left-3 z-10 text-[10px] font-mono text-gray-300 bg-[#111827]/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-[#374151]">
          <span>CALIBRATION: 20.0 px/m | MODEL: YOLOv8n</span>
        </div>

        <div className="absolute bottom-3 right-3 z-10 flex items-center gap-2 text-[10px] font-mono text-[#00FFFF] bg-[#111827]/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-[#374151]">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>DEBOUNCE: 3 FRAMES</span>
        </div>
      </div>

      {/* Bottom Telemetry Bar */}
      <div className="flex items-center justify-between text-xs font-mono text-gray-400 pt-2 border-t border-[#374151]/50">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-gray-300">
            <Truck className="w-3.5 h-3.5 text-[#00FFFF]" />
            Target: Haul #1
          </span>
          <span className="flex items-center gap-1.5 text-gray-300">
            <HardHat className="w-3.5 h-3.5 text-[#10B981]" />
            1 Worker Locked
          </span>
        </div>
        <span className="text-[11px] text-gray-400">
          Codec: MP4V / Circular Ring Buffer Active
        </span>
      </div>
    </div>
  );
}
