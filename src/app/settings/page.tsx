"use client";

import React, { useState } from "react";
import {
  Sliders,
  Shield,
  Bell,
  Save,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";

export default function SettingsPage(): React.JSX.Element {
  const [criticalDist, setCriticalDist] = useState<number>(3.0);
  const [warningDist, setWarningDist] = useState<number>(10.0);
  const [pixelsPerMeter, setPixelsPerMeter] = useState<number>(20.0);
  const [cooldownSec, setCooldownSec] = useState<number>(60);
  const [debounceFrames, setDebounceFrames] = useState<number>(3);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleReset = () => {
    setCriticalDist(3.0);
    setWarningDist(10.0);
    setPixelsPerMeter(20.0);
    setCooldownSec(60);
    setDebounceFrames(3);
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Top Banner */}
      <div className="p-5 rounded-2xl bg-[#1f2937]/90 border border-[#374151] flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-[#00FFFF]" />
            Safety Thresholds & System Calibration
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Configure real-time monocular vision thresholds, debounce parameters,
            and cloud notification channels.
          </p>
        </div>

        {savedSuccess && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#10B981]/20 border border-[#10B981]/40 text-xs font-mono font-bold text-[#10B981] animate-fade-in">
            <CheckCircle2 className="w-4 h-4" />
            <span>CONFIG SAVED</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: Spatial Proximity Calibration */}
        <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-[#374151]/60">
            <Shield className="w-4 h-4 text-[#00FFFF]" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Spatial Halo & Distance Calibration
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
            <div>
              <label className="block text-gray-300 font-medium mb-1.5">
                Critical Safety Halo Distance (Meters)
              </label>
              <input
                type="number"
                step="0.5"
                min="1.0"
                max="10.0"
                value={criticalDist}
                onChange={(e) => setCriticalDist(parseFloat(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-white font-mono focus:outline-none focus:border-[#00FFFF]"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Distances under this value trigger immediate emergency siren and
                supervisor dispatch.
              </p>
            </div>

            <div>
              <label className="block text-gray-300 font-medium mb-1.5">
                Warning Safety Halo Distance (Meters)
              </label>
              <input
                type="number"
                step="0.5"
                min="3.0"
                max="25.0"
                value={warningDist}
                onChange={(e) => setWarningDist(parseFloat(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-white font-mono focus:outline-none focus:border-[#00FFFF]"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Yellow alert boundary. Workers approaching inside this radius
                receive cockpit advisory.
              </p>
            </div>

            <div>
              <label className="block text-gray-300 font-medium mb-1.5">
                Camera Pixel-To-Meter Calibration Constant (px/m)
              </label>
              <input
                type="number"
                step="1.0"
                min="5.0"
                max="100.0"
                value={pixelsPerMeter}
                onChange={(e) => setPixelsPerMeter(parseFloat(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-white font-mono focus:outline-none focus:border-[#00FFFF]"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Monocular camera baseline conversion factor (default: 20.0 px =
                1.0 meter).
              </p>
            </div>

            <div>
              <label className="block text-gray-300 font-medium mb-1.5">
                Debounce Confirmation Window (Consecutive Frames)
              </label>
              <input
                type="number"
                step="1"
                min="1"
                max="10"
                value={debounceFrames}
                onChange={(e) => setDebounceFrames(parseInt(e.target.value, 10))}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-white font-mono focus:outline-none focus:border-[#00FFFF]"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Require N consecutive critical frames before dispatching alarm
                (prevents transient false alerts).
              </p>
            </div>
          </div>
        </div>

        {/* Section 2: Alert Cooldown & Cloud Storage */}
        <div className="p-6 rounded-2xl bg-[#1f2937]/90 border border-[#374151] space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-[#374151]/60">
            <Bell className="w-4 h-4 text-[#00FFFF]" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Notifications & Storage Integration
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
            <div>
              <label className="block text-gray-300 font-medium mb-1.5">
                Alert Cooldown Window (Seconds)
              </label>
              <input
                type="number"
                step="5"
                min="10"
                max="600"
                value={cooldownSec}
                onChange={(e) => setCooldownSec(parseInt(e.target.value, 10))}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-white font-mono focus:outline-none focus:border-[#00FFFF]"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Suppress duplicate emails for the same worker-machine pair within
                this duration.
              </p>
            </div>

            <div>
              <label className="block text-gray-300 font-medium mb-1.5">
                Supervisor Email Gateway (Resend)
              </label>
              <input
                type="email"
                defaultValue="safety-lead@halocas-mine.internal"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#111827] border border-[#374151] text-white font-mono focus:outline-none focus:border-[#00FFFF]"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Default recipient for automated HTML incident notifications.
              </p>
            </div>
          </div>
        </div>

        {/* Form Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-[#111827] border border-[#374151] hover:border-gray-400 text-xs font-semibold text-gray-300 hover:text-white transition-all"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>
          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90 transition-all shadow-cyan-glow"
          >
            <Save className="w-4 h-4" />
            <span>Save Configuration</span>
          </button>
        </div>
      </form>
    </div>
  );
}
