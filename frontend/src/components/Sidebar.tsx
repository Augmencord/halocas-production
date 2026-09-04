"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  AlertTriangle,
  Users,
  Truck,
  Settings,
  Shield,
  Menu,
  X,
  Activity,
  HardHat,
} from "lucide-react";
import { cn } from "../lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeVariant?: "cyan" | "red" | "green";
}

const navItems: NavItem[] = [
  {
    name: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Live Monitoring",
    href: "/monitoring",
    icon: Radio,
    badge: "LIVE",
    badgeVariant: "cyan",
  },
  {
    name: "Incidents",
    href: "/incidents",
    icon: AlertTriangle,
    badge: "3",
    badgeVariant: "red",
  },
  {
    name: "Workers",
    href: "/workers",
    icon: Users,
  },
  {
    name: "Machines",
    href: "/machines",
    icon: Truck,
  },
  {
    name: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

export default function Sidebar(): React.JSX.Element {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Mobile Toggle Button */}
      <div className="lg:hidden fixed top-3 left-4 z-50">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-2 rounded-lg bg-panel border border-border text-gray-200 hover:text-cyan focus:outline-none"
          aria-label="Toggle Navigation"
        >
          {isOpen ? <X className="w-6 h-6 text-cyan" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed top-0 left-0 bottom-0 z-40 w-64 md:w-72 bg-[#111827] border-r border-[#374151] flex flex-col justify-between transition-transform duration-300 ease-in-out lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Top Brand Header */}
        <div className="p-5 border-b border-[#374151]/80">
          <div className="flex items-center space-x-3">
            <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-[#1f2937] to-[#111827] border border-[#00FFFF]/40 shadow-cyan-glow">
              <Shield className="w-6 h-6 text-[#00FFFF]" />
              <span className="absolute top-1 right-1 w-2.5 h-2.5 rounded-full bg-[#00FFFF] animate-beacon" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-extrabold tracking-wider text-white font-mono">
                  HALO<span className="text-[#00FFFF]">CAS</span>
                </span>
                <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-[#00FFFF]/10 text-[#00FFFF] border border-[#00FFFF]/30">
                  PROD
                </span>
              </div>
              <p className="text-[11px] text-gray-400 tracking-tight flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                Collision Avoidance Active
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto">
          <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400 font-mono">
            Command Navigation
          </div>
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={cn(
                  "group relative flex items-center justify-between px-3.5 py-3 rounded-xl text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-[#1f2937] text-white border border-[#00FFFF]/40 shadow-[0_0_15px_rgba(0,255,255,0.15)]"
                    : "text-gray-400 hover:text-gray-100 hover:bg-[#1f2937]/60 hover:border hover:border-[#374151]"
                )}
              >
                <div className="flex items-center space-x-3.5">
                  <div
                    className={cn(
                      "p-1.5 rounded-lg transition-colors",
                      isActive
                        ? "bg-[#00FFFF]/10 text-[#00FFFF]"
                        : "text-gray-400 group-hover:text-[#00FFFF]"
                    )}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="tracking-wide">{item.name}</span>
                </div>

                {/* Badges */}
                {item.badge && (
                  <span
                    className={cn(
                      "text-[10px] font-mono font-bold px-2 py-0.5 rounded-full uppercase tracking-wider",
                      item.badgeVariant === "cyan" &&
                        "bg-[#00FFFF]/15 text-[#00FFFF] border border-[#00FFFF]/30",
                      item.badgeVariant === "red" &&
                        "bg-[#FF3B30]/15 text-[#FF3B30] border border-[#FF3B30]/30 animate-pulse",
                      item.badgeVariant === "green" &&
                        "bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30"
                    )}
                  >
                    {item.badge}
                  </span>
                )}

                {/* Active Indicator Bar */}
                {isActive && (
                  <span className="absolute left-0 top-2 bottom-2 w-1 bg-[#00FFFF] rounded-r-full shadow-[0_0_8px_#00FFFF]" />
                )}
              </Link>
            );
          })}

          {/* Telemetry Status Card */}
          <div className="pt-6 px-2">
            <div className="p-3.5 rounded-xl bg-[#1f2937]/70 border border-[#374151] space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-[#00FFFF]" />
                  Telemetry Link
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30">
                  CONNECTED
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-center text-[11px] font-mono">
                <div className="bg-[#111827]/80 p-1.5 rounded-lg border border-[#374151]/60">
                  <div className="text-gray-400 text-[10px]">INFERENCE</div>
                  <div className="text-white font-bold">14.2 ms</div>
                </div>
                <div className="bg-[#111827]/80 p-1.5 rounded-lg border border-[#374151]/60">
                  <div className="text-gray-400 text-[10px]">FPS</div>
                  <div className="text-[#00FFFF] font-bold">29.8</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Profile Section */}
        <div className="p-4 border-t border-[#374151]/80 bg-[#111827]">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-[#1f2937] border border-[#374151] flex items-center justify-center text-gray-300">
              <HardHat className="w-5 h-5 text-[#00FFFF]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white truncate">
                Safety Supervisor
              </p>
              <p className="text-[11px] text-gray-400 truncate flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                Pit Sector Alpha
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
