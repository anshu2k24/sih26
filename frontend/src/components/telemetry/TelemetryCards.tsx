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
    <div 
      className="rounded-3xl p-6 flex flex-col justify-start"
      style={{
        background: "linear-gradient(145deg, rgba(20, 27, 42, 0.72), rgba(9, 14, 25, 0.60))",
        border: "1px solid rgba(255, 255, 255, 0.12)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        boxShadow: "0 25px 70px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08)"
      }}
    >
      <h2 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-5 flex items-center gap-2">
        <Gauge className="w-4 h-4 text-emerald-400" />
        Real-Time Drilling Parameters
      </h2>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
        {cards.map((c, idx) => {
          const IconComponent = c.icon;
          return (
            <div key={idx} className={`p-3.5 rounded-xl border ${c.bg} bg-[#0B101E]/80 backdrop-blur-sm flex flex-col justify-between transition-all duration-300 hover:-translate-y-1 hover:border-orange-500/50 hover:shadow-[0_0_20px_rgba(255,140,0,0.2)] hover:bg-[#0B101E]`}>
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2.5">
                <span className="truncate text-[11px] font-semibold tracking-wider" title={c.label}>
                  {c.label.split(" ")[0]}
                </span>
                <IconComponent className={`w-4 h-4 ${c.color}`} />
              </div>
              <div>
                <div className={`text-xl font-bold font-mono tracking-wider ${c.color}`}>{c.value}</div>
                <div className="text-[10px] text-slate-500 font-mono mt-0.5 font-semibold">{c.unit}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
