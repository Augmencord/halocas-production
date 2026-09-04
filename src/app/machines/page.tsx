"use client";

import React, { useState } from "react";
import {
  Truck,
  Search,
  Radio,
  MapPin,
  Clock,
} from "lucide-react";

interface MachineRecord {
  id: string;
  name: string;
  type: string;
  zone: string;
  status: "ACTIVE" | "STANDBY" | "MAINTENANCE";
  speedKmh: number;
  camerasCount: number;
  lastPing: string;
}

const machinesList: MachineRecord[] = [
  {
    id: "CAT-797F-01",
    name: "Caterpillar 797F #1",
    type: "Ultra-Class Haul Truck (400-ton)",
    zone: "Sector 04 - North Cut",
    status: "ACTIVE",
    speedKmh: 24.2,
    camerasCount: 2,
    lastPing: "Just now",
  },
  {
    id: "KOMATSU-930E-03",
    name: "Komatsu 930E-4 #3",
    type: "AC Haul Truck (320-ton)",
    zone: "Haul Road Alpha",
    status: "ACTIVE",
    speedKmh: 31.0,
    camerasCount: 2,
    lastPing: "Just now",
  },
  {
    id: "HITACHI-EX8000-02",
    name: "Hitachi EX8000-6 #2",
    type: "Hydraulic Mining Shovel",
    zone: "Sector 04 - Bench 3",
    status: "ACTIVE",
    speedKmh: 0.0,
    camerasCount: 3,
    lastPing: "Just now",
  },
  {
    id: "CAT-994K-05",
    name: "Caterpillar 994K #5",
    type: "Wheel Loader",
    zone: "Stockpile Bravo",
    status: "STANDBY",
    speedKmh: 0.0,
    camerasCount: 1,
    lastPing: "3 mins ago",
  },
  {
    id: "KOMATSU-830E-04",
    name: "Komatsu 830E-AC #4",
    type: "Electric Drive Haul Truck",
    zone: "Maintenance Bay 2",
    status: "MAINTENANCE",
    speedKmh: 0.0,
    camerasCount: 0,
    lastPing: "42 mins ago",
  },
];

export default function MachinesPage(): React.JSX.Element {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");

  const filteredMachines = machinesList.filter((m) => {
    const matchesStatus =
      selectedStatus === "ALL" || m.status === selectedStatus;
    const matchesSearch =
      m.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.zone.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
          <span className="text-xs text-gray-400 font-mono uppercase">
            Total Fleet Assets
          </span>
          <div className="text-2xl font-bold text-white font-mono mt-1">10</div>
        </div>
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
          <span className="text-xs text-gray-400 font-mono uppercase">
            Active in Proximity Loop
          </span>
          <div className="text-2xl font-bold text-[#10B981] font-mono mt-1">
            8 Units
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
          <span className="text-xs text-gray-400 font-mono uppercase">
            Standby / Idling
          </span>
          <div className="text-2xl font-bold text-[#F59E0B] font-mono mt-1">
            1 Unit
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
          <span className="text-xs text-gray-400 font-mono uppercase">
            Scheduled Service
          </span>
          <div className="text-2xl font-bold text-gray-400 font-mono mt-1">
            1 Unit
          </div>
        </div>
      </div>

      {/* Control / Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-[#1f2937]/90 border border-[#374151]">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search machines by ID, model, or pit zone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF]"
          />
        </div>

        <div className="flex items-center gap-2">
          {["ALL", "ACTIVE", "STANDBY", "MAINTENANCE"].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all ${
                selectedStatus === st
                  ? "bg-[#00FFFF] text-[#111827] shadow-cyan-glow"
                  : "bg-[#111827] text-gray-400 hover:text-white border border-[#374151]"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Fleet Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredMachines.map((machine) => (
          <div
            key={machine.id}
            className="p-5 rounded-2xl bg-[#1f2937]/90 border border-[#374151] hover:border-[#00FFFF]/50 transition-all space-y-4"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-[#111827] border border-[#374151] text-[#00FFFF]">
                  <Truck className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white font-mono">
                    {machine.id}
                  </h4>
                  <p className="text-xs text-gray-400">{machine.name}</p>
                </div>
              </div>

              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                  machine.status === "ACTIVE"
                    ? "bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30"
                    : machine.status === "STANDBY"
                    ? "bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30"
                    : "bg-gray-700/50 text-gray-400 border border-gray-600"
                }`}
              >
                {machine.status}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between text-gray-400">
                <span className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-[#00FFFF]" />
                  Operational Zone:
                </span>
                <span className="text-gray-200 font-medium">{machine.zone}</span>
              </div>
              <div className="flex items-center justify-between text-gray-400">
                <span className="flex items-center gap-1.5">
                  <Radio className="w-3.5 h-3.5 text-[#10B981]" />
                  Telemetry Speed:
                </span>
                <span className="font-mono text-white font-bold">
                  {machine.speedKmh} km/h
                </span>
              </div>
              <div className="flex items-center justify-between text-gray-400">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  Sensors Mounted:
                </span>
                <span className="font-mono text-gray-300">
                  {machine.camerasCount} Cameras Linked
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-[#374151]/60 flex items-center justify-between text-[11px] font-mono text-gray-400">
              <span>Ping: {machine.lastPing}</span>
              <span className="text-[#00FFFF] hover:underline cursor-pointer">
                View Feeds &rarr;
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
