import React, { useEffect, useRef, useState } from "react";
import type { MLStatusState } from "../../types/ml";
import { Activity, BarChart2, Radio, Zap, AlertTriangle, CheckCircle2 } from "lucide-react";

interface RiskCenterProps {
  mlState: MLStatusState;
  latestSensor?: Record<string, any> | null;
  currentMd?: number;
}

// ── Ring Gauge ───────────────────────────────────────────────────────────────
function RiskGauge({ score }: { score: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.beginPath();
    ctx.arc(w / 2, h * 0.78, h * 0.62, Math.PI, 0, false);
    ctx.lineWidth = 12;
    ctx.strokeStyle = "rgba(255,255,255,0.07)";
    ctx.stroke();
    const color = score >= 1.0 ? "#f43f5e" : "#10b981";
    ctx.shadowColor = color;
    ctx.shadowBlur = 20;
    ctx.beginPath();
    ctx.arc(w / 2, h * 0.78, h * 0.62, Math.PI, Math.PI + score * Math.PI, false);
    ctx.lineWidth = 12;
    ctx.strokeStyle = color;
    ctx.lineCap = "round";
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.fillStyle = color;
    ctx.font = `bold ${h * 0.22}px 'Space Grotesk', monospace`;
    ctx.textAlign = "center";
    ctx.fillText(score >= 1.0 ? "ANOMALY" : "NORMAL", w / 2, h * 0.65);
  }, [score]);
  return <canvas ref={canvasRef} width={200} height={110} className="mx-auto" />;
}

// ── Animated number that flashes when value changes ───────────────────────
function LiveValue({ value, unit = "", fmt = 1 }: { value?: number | null; unit?: string; fmt?: number }) {
  const [flash, setFlash] = useState(false);
  const prev = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (value !== undefined && value !== prev.current) {
      prev.current = value ?? undefined;
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 350);
      return () => clearTimeout(t);
    }
  }, [value]);

  if (value === undefined || value === null) return <span style={{ color: "rgba(255,255,255,0.2)" }}>—</span>;

  return (
    <span
      style={{
        color: flash ? "#ff9b4a" : "rgba(255,255,255,0.92)",
        transition: "color 0.35s ease",
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {value.toFixed(fmt)}{unit}
    </span>
  );
}

// ── Single row in the scrolling feed ────────────────────────────────────────
interface FeedRow {
  id: number;
  md: number;
  ts: string;
  rop?: number | null;
  wob?: number | null;
  spp?: number | null;
  torque?: number | null;
  rpm?: number | null;
  flow?: number | null;
  verdict: "ANOMALY" | "NORMAL" | "LOADING";
}

const MAX_FEED = 60;

// ── Main Component ────────────────────────────────────────────────────────────
export const RiskCenter: React.FC<RiskCenterProps> = ({ mlState, latestSensor, currentMd }) => {
  const isActive = mlState.status === "SUCCESS" && !mlState.is_blocked;
  const isAnomaly = isActive && mlState.risk_score === 1.0;
  const riskScore = mlState.risk_score ?? 0;

  const [feed, setFeed] = useState<FeedRow[]>([]);
  const rowId = useRef(0);

  // Append a new row whenever latestSensor changes
  useEffect(() => {
    if (!latestSensor || !latestSensor.md) return;
    const verdict: FeedRow["verdict"] =
      mlState.status === "SUCCESS"
        ? mlState.risk_score === 1.0 ? "ANOMALY" : "NORMAL"
        : "LOADING";

    const row: FeedRow = {
      id: rowId.current++,
      md: latestSensor.md,
      ts: latestSensor.timestamp ? new Date(latestSensor.timestamp).toLocaleTimeString() : "—",
      rop: latestSensor.rop,
      wob: latestSensor.wob,
      spp: latestSensor.spp,
      torque: latestSensor.torque,
      rpm: latestSensor.rpm,
      flow: latestSensor.flow_in,
      verdict,
    };
    setFeed((prev) => [row, ...prev].slice(0, MAX_FEED));
  }, [latestSensor?.md]);

  const orange = "#ff8a1f";
  const orangeLight = "#ff9b4a";
  const anomalyRed = "#f43f5e";
  const normalGreen = "#10b981";
  const verdictColor = isAnomaly ? anomalyRed : isActive ? normalGreen : orangeLight;

  const glassCard = {
    background: "linear-gradient(145deg, rgba(20,27,42,0.72), rgba(9,14,25,0.60))",
    border: "1px solid rgba(255,255,255,0.08)",
    backdropFilter: "blur(18px)",
    WebkitBackdropFilter: "blur(18px)",
    boxShadow: "0 25px 70px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)",
  } as React.CSSProperties;

  return (
    <div className="space-y-4">
      {/* ── Top section: gauge + verdict ── */}
      <div
        style={{
          ...glassCard,
          border: `1px solid ${isAnomaly ? "rgba(244,63,94,0.35)" : isActive ? "rgba(16,185,129,0.22)" : "rgba(255,255,255,0.08)"}`,
          boxShadow: isAnomaly
            ? "0 25px 70px rgba(244,63,94,0.15), inset 0 1px 0 rgba(255,255,255,0.06)"
            : glassCard.boxShadow,
          transition: "all 0.5s ease",
        }}
        className="rounded-2xl p-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3 mb-5">
          <div className="flex items-center gap-3">
            <div style={{ background: "linear-gradient(135deg, #ff9b2f, #ff7a18)", boxShadow: "0 6px 20px rgba(255,122,24,0.3)" }}
              className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <p style={{ color: orangeLight, letterSpacing: "2px" }} className="text-[10px] font-bold uppercase">PREDICTIVE RISK CENTER</p>
              <h2 className="text-white font-bold text-sm">Isolation Forest · Real-Time Inference</h2>
            </div>
          </div>
          <div style={{
            background: isAnomaly ? "rgba(244,63,94,0.12)" : isActive ? "rgba(16,185,129,0.10)" : "rgba(255,138,31,0.10)",
            border: `1px solid ${isAnomaly ? "rgba(244,63,94,0.35)" : isActive ? "rgba(16,185,129,0.3)" : "rgba(255,138,31,0.25)"}`,
            color: verdictColor,
          }} className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold font-mono">
            {isActive ? <><Radio className="w-3 h-3 animate-pulse" />{isAnomaly ? "ANOMALY ACTIVE" : "NOMINAL — PASS"}</> :
              <><div className="w-2 h-2 rounded-full animate-pulse" style={{ background: orange }} />WARMING UP</>}
          </div>
        </div>

        {isActive ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {/* Gauge */}
            <div className="flex flex-col items-center gap-2">
              <RiskGauge score={riskScore} />
              <div className="flex gap-5 text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.35)" }}>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ background: normalGreen }} />NORMAL</span>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ background: anomalyRed }} />ANOMALY</span>
              </div>
            </div>

            {/* Verdict + live values */}
            <div className="space-y-3">
              <div style={{
                background: isAnomaly ? "rgba(244,63,94,0.08)" : "rgba(16,185,129,0.08)",
                border: `1px solid ${isAnomaly ? "rgba(244,63,94,0.3)" : "rgba(16,185,129,0.25)"}`,
              }} className="p-4 rounded-xl flex items-start gap-3">
                {isAnomaly
                  ? <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: anomalyRed }} />
                  : <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" style={{ color: normalGreen }} />}
                <div>
                  <div className="font-bold text-white text-sm">{isAnomaly ? "ANOMALOUS TELEMETRY" : "NOMINAL OPERATION"}</div>
                  <div className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>
                    {isAnomaly ? "Hazard classified — see Alerts page for specific diagnosis and recommended action." : "All channels within expected bounds."}
                  </div>
                </div>
              </div>

              {/* Live sensor snapshot — animated */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                {[
                  { label: "ROP", value: latestSensor?.rop, unit: " m/h" },
                  { label: "WOB", value: latestSensor?.wob, unit: " kN" },
                  { label: "SPP", value: latestSensor?.spp, unit: " bar" },
                  { label: "Torque", value: latestSensor?.torque, unit: " kNm" },
                  { label: "RPM", value: latestSensor?.rpm, unit: "", fmt: 0 },
                  { label: "Flow", value: latestSensor?.flow_in, unit: " L/m", fmt: 0 },
                ].map(({ label, value, unit, fmt }) => (
                  <div key={label} style={{ background: "rgba(255,255,255,0.035)", border: "1px solid rgba(255,255,255,0.07)" }}
                    className="rounded-xl p-2.5">
                    <div style={{ color: "rgba(255,255,255,0.35)" }} className="text-[10px] uppercase tracking-wider mb-1">{label}</div>
                    <div className="font-bold">
                      <LiveValue value={value} unit={unit} fmt={fmt ?? 1} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-5 py-10">
            <div className="relative">
              <div style={{ border: "2px solid rgba(255,138,31,0.2)", background: "rgba(255,138,31,0.05)" }}
                className="w-16 h-16 rounded-full flex items-center justify-center">
                <Activity className="w-7 h-7" style={{ color: orange }} />
              </div>
              <div className="absolute inset-0 rounded-full border-2 animate-ping" style={{ borderColor: "rgba(255,138,31,0.2)" }} />
            </div>
            <div className="text-center space-y-2">
              <p style={{ color: orangeLight, letterSpacing: "1px" }} className="text-sm font-bold uppercase font-mono">Building Causal Feature Window...</p>
              <p className="text-xs max-w-xs" style={{ color: "rgba(255,255,255,0.4)" }}>{mlState.gate_reason || "Waiting for sufficient telemetry."}</p>
            </div>
            <div style={{ width: "36px", height: "3px", background: orange, boxShadow: "0 0 12px rgba(255,138,31,0.5)", borderRadius: "10px" }} />
          </div>
        )}

        {/* Footer */}
        <div style={{ borderTopColor: "rgba(255,255,255,0.07)" }} className="pt-4 border-t mt-5 flex items-center justify-between text-[11px] font-mono">
          <span className="flex items-center gap-1.5" style={{ color: "rgba(255,255,255,0.3)" }}>
            <BarChart2 className="w-3.5 h-3.5" style={{ color: orange }} />Causal Feature Builder
          </span>
          <span className="flex items-center gap-1.5" style={{ color: "rgba(255,255,255,0.3)" }}>
            <Activity className="w-3 h-3" style={{ color: orange }} />
            <span style={{ color: orange }} className="font-bold">{mlState.features_constructed ?? 0}</span>
            <span>features</span>
          </span>
        </div>
      </div>

      {/* ── Live Stream Feed ──────────────────────────────────────────────── */}
      <div style={glassCard} className="rounded-2xl overflow-hidden">
        {/* Feed header */}
        <div style={{ borderBottomColor: "rgba(255,255,255,0.07)" }}
          className="flex items-center justify-between px-5 py-3.5 border-b">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#10b981", boxShadow: "0 0 8px #10b981" }} />
            <span style={{ color: orangeLight, letterSpacing: "2px" }} className="text-[10px] font-bold uppercase">
              Live Telemetry Feed
            </span>
            <span style={{ color: "rgba(255,255,255,0.3)", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}
              className="text-[10px] px-2 py-0.5 rounded font-mono">
              {feed.length} samples
            </span>
          </div>
          <span style={{ color: "rgba(255,255,255,0.25)" }} className="text-[10px] font-mono">
            Isolation Forest scoring every tick
          </span>
        </div>

        {/* Column headers */}
        <div
          className="grid grid-cols-9 gap-0 px-4 py-2 border-b text-[10px] font-bold uppercase tracking-widest"
          style={{ background: "rgba(255,255,255,0.03)", borderBottomColor: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.3)" }}>
          <span>TIME</span>
          <span>MD (m)</span>
          <span>ROP m/h</span>
          <span>WOB kN</span>
          <span>SPP bar</span>
          <span>Torque</span>
          <span>RPM</span>
          <span>Flow L/m</span>
          <span className="text-right">VERDICT</span>
        </div>

        {/* Scrollable rows */}
        <div style={{ maxHeight: "340px", overflowY: "auto" }}>
          {feed.length === 0 ? (
            <div className="flex items-center justify-center py-16 text-xs" style={{ color: "rgba(255,255,255,0.2)" }}>
              Waiting for stream data...
            </div>
          ) : (
            feed.map((row, idx) => {
              const isNew = idx === 0;
              const rowAnomaly = row.verdict === "ANOMALY";
              return (
                <div
                  key={row.id}
                  className="grid grid-cols-9 gap-0 px-4 py-2 text-xs font-mono transition-all duration-300"
                  style={{
                    background: isNew
                      ? rowAnomaly ? "rgba(244,63,94,0.12)" : "rgba(16,185,129,0.07)"
                      : "transparent",
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    color: "rgba(255,255,255,0.7)",
                    borderLeft: `3px solid ${rowAnomaly ? "#f43f5e" : isNew ? "#10b981" : "transparent"}`,
                  }}
                >
                  <span style={{ color: "rgba(255,255,255,0.35)" }}>{row.ts}</span>
                  <span style={{ color: "#ff9b4a", fontWeight: "bold" }}>{row.md.toFixed(1)}</span>
                  <span>{row.rop != null ? row.rop.toFixed(1) : "—"}</span>
                  <span>{row.wob != null ? row.wob.toFixed(1) : "—"}</span>
                  <span>{row.spp != null ? row.spp.toFixed(1) : "—"}</span>
                  <span>{row.torque != null ? row.torque.toFixed(2) : "—"}</span>
                  <span>{row.rpm != null ? Math.round(row.rpm) : "—"}</span>
                  <span>{row.flow != null ? Math.round(row.flow) : "—"}</span>
                  <span className="text-right font-bold" style={{
                    color: rowAnomaly ? "#f43f5e" : row.verdict === "NORMAL" ? "#10b981" : "rgba(255,255,255,0.3)",
                  }}>
                    {rowAnomaly ? "⚠ ANOMALY" : row.verdict === "NORMAL" ? "✓ NORMAL" : "…"}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
