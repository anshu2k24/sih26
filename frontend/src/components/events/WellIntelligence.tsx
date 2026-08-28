import React from "react";
import type { EventsResponse } from "../../types/events";
import { Database, FileText, ShieldCheck } from "lucide-react";

interface WellIntelligenceProps {
  nwisData: EventsResponse | null;
  activeWell: string;
  currentMd: number;
}

export const WellIntelligence: React.FC<WellIntelligenceProps> = ({
  nwisData,
  activeWell,
  currentMd,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-400" />
            Historical NWIS Intelligence (Offset DDR Database)
          </h2>
          <span className="text-xs px-2.5 py-0.5 rounded bg-blue-950/80 text-blue-400 border border-blue-500/30 font-mono font-medium">
            HISTORICAL DDR
          </span>
        </div>

        {/* Visual Distinction Callout */}
        <div className="p-3 bg-slate-850/80 rounded-lg border border-slate-800 text-xs text-slate-300 mb-4 flex items-center gap-2 font-mono">
          <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0" />
          <span>
            Querying Equinor Volve historical offset well events around active well <strong>{activeWell}</strong> at MD <strong>{currentMd.toFixed(1)}m</strong>.
          </span>
        </div>

        {/* Risk Summary */}
        <div className="mb-4 text-xs font-semibold text-slate-200">
          {nwisData ? nwisData.risk_summary : "Loading historical DDR offset intelligence..."}
        </div>

        {/* Event Cards */}
        {nwisData && nwisData.nearby_events && nwisData.nearby_events.length > 0 ? (
          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {nwisData.nearby_events.map((ev, idx) => (
              <div
                key={idx}
                className="bg-slate-850/60 p-3.5 rounded-lg border border-slate-800 space-y-1.5 text-xs text-slate-300"
              >
                <div className="flex items-center justify-between font-mono font-bold text-slate-200">
                  <span className="text-blue-400">
                    {ev.event_type} @ {ev.onset_md}m
                  </span>
                  <span className="text-slate-400 text-[11px]">
                    Offset Well: {ev.offset_wellbore} (Dist: {ev.depth_distance_m.toFixed(1)}m)
                  </span>
                </div>

                <div className="leading-relaxed">
                  <strong className="text-slate-400">Evidence:</strong> {ev.primary_evidence}
                </div>

                {ev.mitigation && ev.mitigation !== "None recorded" && (
                  <div className="text-amber-300/90 leading-relaxed">
                    <strong className="text-amber-400">Mitigation:</strong> {ev.mitigation}
                  </div>
                )}

                <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono pt-1">
                  <FileText className="w-3 h-3 text-slate-400" />
                  <span>Source DDR Record:</span>
                  <code className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800 text-slate-300">
                    {ev.source_ddr_record}
                  </code>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center border border-dashed border-slate-800 rounded-lg text-slate-400 text-xs font-mono">
            No historical DDR offset events encountered within current depth window.
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800 text-[10px] text-slate-400 font-mono">
        {nwisData?.provenance || "Deterministic intelligence extracted from Equinor Volve semantic DDR database."}
      </div>
    </div>
  );
};
