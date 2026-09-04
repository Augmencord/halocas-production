"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface RadarTarget {
  id: string;
  type: "machine" | "worker";
  name: string;
  distance: number; // in meters
  angle: number; // in radians, 0 is North/up
  severity: "SAFE" | "WARNING" | "CRITICAL";
  authorized?: boolean;
}

export interface TelemetryMessage {
  timestamp?: number;
  camera_id?: string;
  events?: Array<{
    worker_id?: number | string;
    worker_name?: string;
    machine_id?: number | string;
    distance_meters?: number;
    severity?: "SAFE" | "WARNING" | "CRITICAL";
    closing_velocity?: number;
  }>;
  fps?: number;
  latency_ms?: number;
}

export function useWebSocket(): {
  isConnected: boolean;
  status: "CONNECTING" | "OPEN" | "CLOSED";
  targets: RadarTarget[];
  fps: number;
  latencyMs: number;
} {
  const [status, setStatus] = useState<"CONNECTING" | "OPEN" | "CLOSED">("CONNECTING");
  const [targets, setTargets] = useState<RadarTarget[]>([
    {
      id: "mach-cat-797f",
      type: "machine",
      name: "CAT-797F-01",
      distance: 0,
      angle: 0,
      severity: "SAFE",
    },
    {
      id: "w-marcus",
      type: "worker",
      name: "M. Vance",
      distance: 2.3,
      angle: 1.15, // ~65 deg
      severity: "CRITICAL",
      authorized: false,
    },
    {
      id: "w-elena",
      type: "worker",
      name: "E. Rostova",
      distance: 6.8,
      angle: 3.8, // ~218 deg
      severity: "WARNING",
      authorized: true,
    },
    {
      id: "w-chen",
      type: "worker",
      name: "D. Chen",
      distance: 12.4,
      angle: 5.2, // ~298 deg
      severity: "SAFE",
      authorized: false,
    },
  ]);
  const [fps, setFps] = useState<number>(29.8);
  const [latencyMs, setLatencyMs] = useState<number>(14.2);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectRef = useRef<(() => void) | null>(null);

  const connect = useCallback(() => {
    const wsUrl =
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws/telemetry";

    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setStatus("OPEN");
      };

      ws.onmessage = (event) => {
        try {
          const data: TelemetryMessage = JSON.parse(event.data);
          if (data.fps) setFps(data.fps);
          if (data.latency_ms) setLatencyMs(data.latency_ms);

          if (data.events && data.events.length > 0) {
            const updatedTargets: RadarTarget[] = [
              {
                id: "mach-primary",
                type: "machine",
                name: "PRIMARY-HAUL",
                distance: 0,
                angle: 0,
                severity: "SAFE",
              },
            ];

            data.events.forEach((ev, idx) => {
              const dist = ev.distance_meters ?? 5.0;
              const angle = (idx * 1.8 + Math.PI / 4) % (2 * Math.PI);
              updatedTargets.push({
                id: `worker-${ev.worker_id || idx}`,
                type: "worker",
                name: ev.worker_name || `Worker #${ev.worker_id || idx}`,
                distance: dist,
                angle,
                severity:
                  dist < 3.0
                    ? "CRITICAL"
                    : dist < 10.0
                    ? "WARNING"
                    : "SAFE",
              });
            });

            setTargets(updatedTargets);
          }
        } catch {
          // Ignore parse errors on ping packets
        }
      };

      ws.onclose = () => {
        setStatus("CLOSED");
        reconnectTimeoutRef.current = setTimeout(() => {
          connectRef.current?.();
        }, 3000);
      };

      ws.onerror = () => {
        setStatus("CLOSED");
      };
    } catch {
      setStatus("CLOSED");
      reconnectTimeoutRef.current = setTimeout(() => {
        connectRef.current?.();
      }, 5000);
    }
  }, []);

  useEffect(() => {
    connectRef.current = connect;
    const timer = setTimeout(() => {
      connect();
    }, 0);

    return () => {
      clearTimeout(timer);
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return {
    isConnected: status === "OPEN",
    status,
    targets,
    fps,
    latencyMs,
  };
}
