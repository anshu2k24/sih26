import React, { useMemo } from "react";
import type { SensorRecord } from "../../types/sensor";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { LineChart as LineChartIcon } from "lucide-react";

interface LiveSensorChartsProps {
  history: SensorRecord[];
}

export const LiveSensorCharts: React.FC<LiveSensorChartsProps> = ({ history }) => {
  // Downsample to max 150 points for smooth line rendering if stream history is large
  const chartData = useMemo(() => {
    if (!history || history.length === 0) return [];
    if (history.length <= 150) {
      return history.map((r) => ({
        md: Number(r.md.toFixed(2)),
        rop: r.rop != null ? Number(r.rop.toFixed(2)) : null,
        wob: r.wob != null ? Number(r.wob.toFixed(2)) : null,
        rpm: r.rpm != null ? Number(r.rpm.toFixed(1)) : null,
        torque: r.torque != null ? Number(r.torque.toFixed(2)) : null,
        hookload: r.hookload != null ? Number(r.hookload.toFixed(2)) : null,
        spp: r.spp != null ? Number(r.spp.toFixed(1)) : null,
        flow_in: r.flow_in != null ? Number(r.flow_in.toFixed(1)) : null,
        mud_density: r.mud_density != null ? Number(r.mud_density.toFixed(2)) : null,
      }));
    }
    const step = Math.ceil(history.length / 150);
    return history.filter((_, idx) => idx % step === 0 || idx === history.length - 1).map((r) => ({
      md: Number(r.md.toFixed(2)),
      rop: r.rop != null ? Number(r.rop.toFixed(2)) : null,
      wob: r.wob != null ? Number(r.wob.toFixed(2)) : null,
      rpm: r.rpm != null ? Number(r.rpm.toFixed(1)) : null,
      torque: r.torque != null ? Number(r.torque.toFixed(2)) : null,
      hookload: r.hookload != null ? Number(r.hookload.toFixed(2)) : null,
      spp: r.spp != null ? Number(r.spp.toFixed(1)) : null,
      flow_in: r.flow_in != null ? Number(r.flow_in.toFixed(1)) : null,
      mud_density: r.mud_density != null ? Number(r.mud_density.toFixed(2)) : null,
    }));
  }, [history]);

  const configs = [
    { title: "MD vs ROP", dataKey: "rop", unit: "m/h", color: "#10b981" },
    { title: "MD vs WOB", dataKey: "wob", unit: "kkgf", color: "#3b82f6" },
    { title: "MD vs RPM", dataKey: "rpm", unit: "rpm", color: "#f59e0b" },
    { title: "MD vs Torque", dataKey: "torque", unit: "kN.m", color: "#a855f7" },
    { title: "MD vs Hookload", dataKey: "hookload", unit: "kkgf", color: "#06b6d4" },
    { title: "MD vs SPP", dataKey: "spp", unit: "kPa", color: "#f43f5e" },
    { title: "MD vs Mud Flow In", dataKey: "flow_in", unit: "L/min", color: "#6366f1" },
    { title: "MD vs Mud Density", dataKey: "mud_density", unit: "g/cm³", color: "#14b8a6" },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
        <LineChartIcon className="w-4 h-4 text-cyan-400" />
        Real-Time Sensor Telemetry Line Charts (Emitted Causal History)
      </h2>

      {chartData.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-slate-800 rounded-lg text-slate-400 text-sm">
          No streaming telemetry history received yet. Activate stream simulator to render live charts.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {configs.map((c, idx) => (
            <div key={idx} className="bg-slate-850/60 p-3.5 rounded-lg border border-slate-800 flex flex-col">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2">
                <span>{c.title}</span>
                <span className="font-mono text-[11px]" style={{ color: c.color }}>
                  {c.unit}
                </span>
              </div>

              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="md"
                      stroke="#64748b"
                      tick={{ fill: "#64748b", fontSize: 10 }}
                      unit="m"
                    />
                    <YAxis stroke="#64748b" tick={{ fill: "#64748b", fontSize: 10 }} domain={["auto", "auto"]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.375rem", fontSize: "11px" }}
                      labelStyle={{ color: "#94a3b8", fontWeight: 600 }}
                    />
                    <Line
                      type="monotone"
                      dataKey={c.dataKey}
                      stroke={c.color}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
