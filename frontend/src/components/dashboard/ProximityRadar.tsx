"use client";

import React, { useEffect, useRef } from "react";
import { Radio, Users } from "lucide-react";
import { useWebSocket } from "../../lib/useWebSocket";

export default function ProximityRadar(): React.JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { isConnected, targets, latencyMs } = useWebSocket();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let sweepAngle = 0;

    const render = () => {
      // Resize handling for crisp Retina rendering
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const dpr = window.devicePixelRatio || 1;

      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);

      const centerX = width / 2;
      const centerY = height / 2;
      const maxRadius = Math.min(centerX, centerY) - 24;

      // Scale factor: maxRadius corresponds to ~16 meters
      const scale = maxRadius / 16;

      // 1. Clear background
      ctx.fillStyle = "#0B0F17";
      ctx.fillRect(0, 0, width, height);

      // 2. Draw HUD grid lines
      ctx.strokeStyle = "rgba(55, 65, 81, 0.4)";
      ctx.lineWidth = 1;

      // Crosshairs
      ctx.beginPath();
      ctx.moveTo(centerX, 20);
      ctx.lineTo(centerX, height - 20);
      ctx.moveTo(20, centerY);
      ctx.lineTo(width - 20, centerY);
      ctx.stroke();

      // Diagonal guides
      ctx.strokeStyle = "rgba(55, 65, 81, 0.2)";
      ctx.beginPath();
      ctx.moveTo(centerX - maxRadius, centerY - maxRadius);
      ctx.lineTo(centerX + maxRadius, centerY + maxRadius);
      ctx.moveTo(centerX - maxRadius, centerY + maxRadius);
      ctx.lineTo(centerX + maxRadius, centerY - maxRadius);
      ctx.stroke();

      // 3. Concentric Distance Rings: 3m, 10m, 15m
      const rings = [
        {
          dist: 3.0,
          label: "3m CRITICAL",
          color: "rgba(255, 59, 48, 0.8)",
          fill: "rgba(255, 59, 48, 0.04)",
          dash: [4, 4],
        },
        {
          dist: 10.0,
          label: "10m WARNING",
          color: "rgba(245, 158, 11, 0.7)",
          fill: "rgba(245, 158, 11, 0.02)",
          dash: [6, 6],
        },
        {
          dist: 15.0,
          label: "15m SAFE",
          color: "rgba(55, 65, 81, 0.8)",
          fill: "transparent",
          dash: [8, 8],
        },
      ];

      rings.forEach((ring) => {
        const radius = ring.dist * scale;

        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.fillStyle = ring.fill;
        ctx.fill();

        ctx.setLineDash(ring.dash);
        ctx.strokeStyle = ring.color;
        ctx.lineWidth = ring.dist === 3.0 ? 1.8 : 1.2;
        ctx.stroke();
        ctx.setLineDash([]);

        // Ring Label
        ctx.fillStyle = ring.color;
        ctx.font = "10px monospace";
        ctx.fillText(ring.label, centerX + 6, centerY - radius + 12);
      });

      // 4. Rotating Radar Sweep Beam
      sweepAngle = (sweepAngle + 0.035) % (Math.PI * 2);

      // Gradient Sweep Fan
      const sweepGradient = ctx.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        maxRadius
      );
      sweepGradient.addColorStop(0, "rgba(0, 255, 255, 0.35)");
      sweepGradient.addColorStop(0.8, "rgba(0, 255, 255, 0.15)");
      sweepGradient.addColorStop(1, "rgba(0, 255, 255, 0)");

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(
        centerX,
        centerY,
        maxRadius,
        sweepAngle - 0.45,
        sweepAngle,
        false
      );
      ctx.closePath();
      ctx.fillStyle = sweepGradient;
      ctx.fill();

      // Sharp Leading Sweep Line
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(
        centerX + Math.cos(sweepAngle) * maxRadius,
        centerY + Math.sin(sweepAngle) * maxRadius
      );
      ctx.strokeStyle = "#00FFFF";
      ctx.lineWidth = 2;
      ctx.shadowColor = "#00FFFF";
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.restore();

      // 5. Draw Targets (Machine & Workers)
      targets.forEach((target) => {
        if (target.type === "machine") {
          // Machine center anchor
          ctx.beginPath();
          ctx.arc(centerX, centerY, 8, 0, Math.PI * 2);
          ctx.fillStyle = "#00FFFF";
          ctx.shadowColor = "#00FFFF";
          ctx.shadowBlur = 12;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Outer halo around machine
          ctx.beginPath();
          ctx.arc(centerX, centerY, 14, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(0, 255, 255, 0.5)";
          ctx.lineWidth = 1.5;
          ctx.stroke();

          ctx.fillStyle = "#FFFFFF";
          ctx.font = "bold 9px monospace";
          ctx.fillText("CAT-797F", centerX - 24, centerY + 24);
        } else {
          // Worker blip positioned at target.distance and target.angle
          const r = target.distance * scale;
          const x = centerX + Math.cos(target.angle) * r;
          const y = centerY + Math.sin(target.angle) * r;

          let color = "#10B981"; // Safe
          let haloColor = "rgba(16, 185, 129, 0.3)";

          if (target.severity === "CRITICAL" || target.distance < 3.0) {
            color = "#FF3B30";
            haloColor = "rgba(255, 59, 48, 0.4)";
          } else if (target.severity === "WARNING" || target.distance < 10.0) {
            color = "#F59E0B";
            haloColor = "rgba(245, 158, 11, 0.3)";
          }

          // Expanding pulse for critical targets
          if (target.severity === "CRITICAL") {
            ctx.beginPath();
            ctx.arc(x, y, 14, 0, Math.PI * 2);
            ctx.strokeStyle = haloColor;
            ctx.lineWidth = 2;
            ctx.stroke();
          }

          // Blip dot
          ctx.beginPath();
          ctx.arc(x, y, 6, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.shadowColor = color;
          ctx.shadowBlur = 10;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Target Label
          ctx.fillStyle = "#FFFFFF";
          ctx.font = "10px monospace";
          ctx.fillText(`${target.name} (${target.distance.toFixed(1)}m)`, x + 9, y + 4);
        }
      });

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [targets]);

  return (
    <div className="flex flex-col justify-between rounded-2xl bg-[#1f2937]/90 backdrop-blur-md border border-[#374151] p-5 shadow-2xl overflow-hidden">
      {/* Top Header & Telemetry Status */}
      <div className="flex items-center justify-between pb-3 border-b border-[#374151]/70">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/30 text-[#00FFFF]">
            <Radio className="w-4 h-4 animate-spin" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              2D PROXIMITY RADAR
            </h3>
            <p className="text-[11px] text-gray-400 font-mono">
              BEARING &amp; DISTANCE TO CABIN
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
              isConnected
                ? "bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30"
                : "bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30 animate-pulse"
            }`}
          >
            {isConnected ? "WEBSOCKET LOCKED" : "CONNECTING"}
          </span>
          <span className="hidden sm:inline text-gray-400 bg-[#111827] px-2 py-0.5 rounded border border-[#374151]">
            {latencyMs}ms
          </span>
        </div>
      </div>

      {/* HTML5 Canvas Radar Viewport */}
      <div className="relative my-3 aspect-square w-full rounded-xl bg-[#0B0F17] border border-[#374151] overflow-hidden flex items-center justify-center shadow-inner">
        <canvas
          ref={canvasRef}
          className="w-full h-full cursor-crosshair"
        />

        {/* Legend Overlay on Canvas */}
        <div className="absolute top-3 left-3 flex flex-col gap-1 text-[10px] font-mono bg-[#111827]/85 backdrop-blur-sm px-2.5 py-1.5 rounded-lg border border-[#374151]">
          <span className="flex items-center gap-1.5 text-[#00FFFF] font-bold">
            <span className="w-2 h-2 rounded-full bg-[#00FFFF]" />
            Machine (Origin)
          </span>
          <span className="flex items-center gap-1.5 text-[#FF3B30] font-bold">
            <span className="w-2 h-2 rounded-full bg-[#FF3B30]" />
            &lt; 3m Critical Zone
          </span>
          <span className="flex items-center gap-1.5 text-[#F59E0B]">
            <span className="w-2 h-2 rounded-full bg-[#F59E0B]" />
            &lt; 10m Warning Zone
          </span>
          <span className="flex items-center gap-1.5 text-[#10B981]">
            <span className="w-2 h-2 rounded-full bg-[#10B981]" />
            Safe Zone (&gt; 10m)
          </span>
        </div>

        <div className="absolute bottom-3 right-3 text-[10px] font-mono text-gray-400 bg-[#111827]/85 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-[#374151]">
          <span>ZOOM: 16 METERS | SWEEP: 60 FPS</span>
        </div>
      </div>

      {/* Bottom Target Overview Bar */}
      <div className="pt-2 border-t border-[#374151]/50 flex items-center justify-between text-xs font-mono text-gray-400">
        <div className="flex items-center gap-2">
          <Users className="w-3.5 h-3.5 text-[#00FFFF]" />
          <span>Active Radar Targets:</span>
          <strong className="text-white">{targets.length - 1} Workers</strong>
        </div>
        <span className="text-[11px] text-[#10B981]">
          Hysteresis: +1.0m Active
        </span>
      </div>
    </div>
  );
}
