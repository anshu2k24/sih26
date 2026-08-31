import React, { useState } from "react";
import {
  Calendar,
  Clock,
  Gauge,
  CheckSquare,
  Eye,
  Tag,
  Hash,
  User,
  Copy,
  Check,
} from "lucide-react";
import type { NoteStructuredData } from "../../types/notes";

interface Props {
  data: NoteStructuredData;
}

export const StructuredInfo: React.FC<Props> = ({ data }) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1800);
  };

  const hasContent =
    (data.measurements && data.measurements.length > 0) ||
    (data.tasks && data.tasks.length > 0) ||
    (data.observations && data.observations.length > 0) ||
    (data.entities && data.entities.length > 0) ||
    (data.tags && data.tags.length > 0);

  if (!hasContent) {
    return (
      <div className="p-4 bg-slate-900/40 rounded-xl border border-slate-800 text-center text-slate-500 text-sm">
        No structured engineering entities detected yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Dates & Times row */}
      {(data.date || (data.times && data.times.length > 0)) && (
        <div className="flex flex-wrap gap-2 items-center text-xs">
          {data.date && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-cyan-950/40 text-cyan-300 border border-cyan-800/40 rounded-lg">
              <Calendar className="w-3.5 h-3.5 text-cyan-400" />
              Date: <strong className="font-mono">{data.date}</strong>
            </span>
          )}
          {data.times?.map((t, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-950/40 text-indigo-300 border border-indigo-800/40 rounded-lg"
            >
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              Time: <span className="font-mono">{t}</span>
            </span>
          ))}
        </div>
      )}

      {/* Measurements grid */}
      {data.measurements && data.measurements.length > 0 && (
        <div className="bg-slate-900/60 rounded-xl p-3.5 border border-slate-800">
          <div className="flex items-center justify-between mb-2.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Gauge className="w-3.5 h-3.5 text-amber-400" />
              Engineering Parameters & Measurements ({data.measurements.length})
            </h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data.measurements.map((m, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition"
              >
                <span className="text-xs text-slate-400 truncate max-w-[140px] capitalize">
                  {m.parameter}
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-mono font-semibold text-amber-300 bg-amber-950/30 px-2 py-0.5 rounded border border-amber-800/30">
                    {m.value}
                  </span>
                  <button
                    onClick={() => handleCopy(m.value, `m_${idx}`)}
                    className="text-slate-500 hover:text-slate-300 p-0.5 rounded"
                    title="Copy value"
                  >
                    {copiedKey === `m_${idx}` ? (
                      <Check className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks & Actions */}
      {data.tasks && data.tasks.length > 0 && (
        <div className="bg-slate-900/60 rounded-xl p-3.5 border border-slate-800">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2.5">
            <CheckSquare className="w-3.5 h-3.5 text-emerald-400" />
            Extracted Tasks & Next Steps ({data.tasks.length})
          </h4>
          <ul className="space-y-1.5">
            {data.tasks.map((task, idx) => (
              <li
                key={idx}
                className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/40 p-2 rounded-lg border border-slate-800/60"
              >
                <span className="text-emerald-400 font-mono mt-0.5 font-bold">
                  {idx + 1}.
                </span>
                <span className="flex-1">{task}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Observations */}
      {data.observations && data.observations.length > 0 && (
        <div className="bg-slate-900/60 rounded-xl p-3.5 border border-slate-800">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2.5">
            <Eye className="w-3.5 h-3.5 text-purple-400" />
            Key Observations ({data.observations.length})
          </h4>
          <ul className="space-y-1.5">
            {data.observations.map((obs, idx) => (
              <li
                key={idx}
                className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/40 p-2 rounded-lg border border-slate-800/60"
              >
                <span className="text-purple-400 mt-0.5">•</span>
                <span className="flex-1">{obs}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Entities & Tags */}
      <div className="flex flex-wrap gap-2">
        {data.entities?.map((ent, idx) => (
          <span
            key={idx}
            className="inline-flex items-center gap-1 px-2 py-1 bg-slate-800/80 text-slate-300 rounded text-xs border border-slate-700"
          >
            {ent.role ? <User className="w-3 h-3 text-cyan-400" /> : <Hash className="w-3 h-3 text-amber-400" />}
            <span className="text-slate-400">{ent.type || ent.role}:</span>
            <span className="font-semibold text-slate-200">{ent.value || ent.name}</span>
          </span>
        ))}

        {data.tags?.map((tag, idx) => (
          <span
            key={idx}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-950/50 text-blue-300 rounded-full text-xs border border-blue-800/40"
          >
            <Tag className="w-3 h-3 text-blue-400" />
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
};
