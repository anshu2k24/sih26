import React from "react";
import type { NearbyEvent } from "../../types/events";
import { Layers, AlertTriangle, Disc } from "lucide-react";

interface EventTimelineProps {
  currentMd: number;
  events: NearbyEvent[];
}

type TimelineItem = {
  depth: number;
  type: "event" | "current";
  data?: NearbyEvent;
};

export const EventTimeline: React.FC<EventTimelineProps> = ({ currentMd, events }) => {
  // Sort depth points
  const timelineItems = React.useMemo<TimelineItem[]>(() => {
    const items: TimelineItem[] = events.map((e) => ({
      depth: e.onset_md,
      type: "event",
      data: e,
    }));

    if (currentMd > 0) {
      items.push({
        depth: currentMd,
        type: "current",
      });
    }

    return items.sort((a, b) => a.depth - b.depth);
  }, [currentMd, events]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
        <Layers className="w-4 h-4 text-amber-400" />
        Depth-Oriented Event Timeline (Causal MD Axis)
      </h2>

      {timelineItems.length === 0 ? (
        <div className="p-6 text-center border border-dashed border-slate-800 rounded-lg text-slate-400 text-xs font-mono">
          No historical events found in active depth window.
        </div>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {timelineItems.map((item, idx) => {
            const isCurrent = item.type === "current";
            return (
              <div key={idx} className="relative flex items-start gap-3 group">
                <div
                  className={`absolute -left-6 top-1 w-5 h-5 rounded-full border-2 flex items-center justify-center bg-slate-900 ${
                    isCurrent
                      ? "border-emerald-400 text-emerald-400 animate-pulse"
                      : "border-rose-500 text-rose-400"
                  }`}
                >
                  {isCurrent ? <Disc className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                </div>

                <div
                  className={`p-3 rounded-lg border text-xs w-full transition-all ${
                    isCurrent
                      ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300 shadow-md shadow-emerald-950/20"
                      : "bg-slate-850/60 border-slate-800 text-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between font-mono font-bold">
                    <span>
                      {item.depth.toFixed(1)} m — {isCurrent ? "● CURRENT BIT POSITION" : item.data?.event_type}
                    </span>
                    {!isCurrent && item.data && (
                      <span className="text-[11px] text-slate-400 font-normal">
                        Well: {item.data.offset_wellbore} (Dist: {item.data.depth_distance_m.toFixed(1)}m)
                      </span>
                    )}
                  </div>

                  {!isCurrent && item.data && (
                    <div className="mt-1.5 space-y-1 text-[11px]">
                      <div className="text-slate-300">
                        <strong className="text-slate-400">Evidence:</strong> {item.data.primary_evidence}
                      </div>
                      {item.data.mitigation && item.data.mitigation !== "None recorded" && (
                        <div className="text-amber-300">
                          <strong className="text-amber-400">Mitigation:</strong> {item.data.mitigation}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
