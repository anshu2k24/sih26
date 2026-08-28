import React from "react";
import type { SensorRecord } from "../../types/sensor";
import { Gauge, Gauge as Speedometer, RefreshCw, Zap, Anchor, Droplets, ArrowUpRight } from "lucide-react";

interface TelemetryCardsProps {
  latestSensor: SensorRecord | null;
}

export const TelemetryCards: React.FC<TelemetryCardsProps> = ({ latestSensor }) => {
  const cards = [
    {
      label: "ROP",
      fullLabel: "Rate of Penetration",
      value: latestSensor?.rop != null ? latestSensor.rop.toFixed(2) : "N/A",
      unit: "m/h",
      icon: ArrowUpRight,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/20",
    },
    {
      label: "WOB",
      fullLabel: "Weight on Bit",
      value: latestSensor?.wob != null ? latestSensor.wob.toFixed(2) : "N/A",
      unit: "kkgf",
      icon: Anchor,
      color: "text-blue-400",
      bg: "bg-blue-500/10 border-blue-500/20",
    },
    {
      label: "RPM",
      fullLabel: "Rotary Speed",
      value: latestSensor?.rpm != null ? latestSensor.rpm.toFixed(1) : "N/A",
      unit: "rpm",
      icon: RefreshCw,
      color: "text-amber-400",
      bg: "bg-amber-500/10 border-amber-500/20",
    },
    {
      label: "Torque",
      fullLabel: "Surface Torque",
      value: latestSensor?.torque != null ? latestSensor.torque.toFixed(2) : "N/A",
      unit: "kN·m",
      icon: Zap,
      color: "text-purple-400",
      bg: "bg-purple-500/10 border-purple-500/20",
    },
    {
      label: "Hookload",
      fullLabel: "Total Hookload",
      value: latestSensor?.hookload != null ? latestSensor.hookload.toFixed(2) : "N/A",
      unit: "t",
      icon: Speedometer,
      color: "text-cyan-400",
      bg: "bg-cyan-500/10 border-cyan-500/20",
    },
    {
      label: "SPP",
      fullLabel: "Standpipe Pressure",
      value: latestSensor?.spp != null ? latestSensor.spp.toFixed(1) : "N/A",
      unit: "bar",
      icon: Gauge,
      color: "text-rose-400",
      bg: "bg-rose-500/10 border-rose-500/20",
    },
    {
      label: "Flow Rate",
      fullLabel: "Mud Flow In",
      value: latestSensor?.flow_in != null ? latestSensor.flow_in.toFixed(1) : "N/A",
      unit: "l/min",
      icon: Droplets,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10 border-indigo-500/20",
    },
    {
      label: "Mud Density",
      fullLabel: "Drilling Mud Density",
      value: latestSensor?.mud_density != null ? latestSensor.mud_density.toFixed(2) : "N/A",
      unit: "g/cm³",
      icon: Droplets,
      color: "text-teal-400",
      bg: "bg-teal-500/10 border-teal-500/20",
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
        <Gauge className="w-4 h-4 text-emerald-400" />
        Real-Time Drilling Parameters
      </h2>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {cards.map((c, idx) => {
          const IconComponent = c.icon;
          return (
            <div key={idx} className={`p-3 rounded-lg border ${c.bg} flex flex-col justify-between`}>
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span className="truncate text-[11px] font-medium" title={c.label}>
                  {c.label.split(" ")[0]}
                </span>
                <IconComponent className={`w-3.5 h-3.5 ${c.color}`} />
              </div>
              <div>
                <div className={`text-base font-bold font-mono ${c.color}`}>{c.value}</div>
                <div className="text-[10px] text-slate-400 font-mono">{c.unit}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
