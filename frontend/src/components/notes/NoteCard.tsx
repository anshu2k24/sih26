import React from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Calendar,
  ChevronRight,
  Gauge,
  Tag,
  CheckCircle2,
  Trash2,
} from "lucide-react";
import type { HandwrittenNote } from "../../types/notes";
import { NoteStatusBadge } from "./NoteStatusBadge";
import { getNoteImageUrl } from "../../services/notesApi";

interface Props {
  note: HandwrittenNote;
  onDelete?: (id: string) => void;
}

export const NoteCard: React.FC<Props> = ({ note, onDelete }) => {
  const imageUrl = getNoteImageUrl(note.public_url);
  const snippet = note.verified_text || note.raw_ocr_text || "No text extracted yet.";
  const measurementsCount = note.structured_data?.measurements?.length || 0;
  const tasksCount = note.structured_data?.tasks?.length || 0;

  return (
    <div className="bg-slate-900/60 border border-slate-800/90 rounded-2xl p-5 hover:border-slate-700 hover:bg-slate-900/90 transition shadow-lg hover:shadow-xl flex flex-col justify-between group">
      <div>
        {/* Header: Title & Badges */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-slate-100 group-hover:text-blue-300 transition truncate">
              {note.title}
            </h3>
            <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
              <Calendar className="w-3 h-3 text-slate-500" />
              <span>{new Date(note.created_at).toLocaleDateString()}</span>
              {note.structured_data?.date && (
                <span className="text-cyan-400 font-mono">
                  • {note.structured_data.date}
                </span>
              )}
            </div>
          </div>
          <NoteStatusBadge
            verificationStatus={note.verification_status}
            ocrStatus={note.ocr_status}
            size="sm"
          />
        </div>

        {/* Thumbnail + Excerpt */}
        <div className="flex gap-3 mb-4">
          {imageUrl ? (
            <div className="w-20 h-20 rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
              <img
                src={imageUrl}
                alt={note.title}
                className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
              />
            </div>
          ) : (
            <div className="w-20 h-20 rounded-xl bg-slate-950 border border-slate-800 shrink-0 flex items-center justify-center text-slate-600">
              <FileText className="w-7 h-7" />
            </div>
          )}

          <div className="flex-1 min-w-0">
            <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed font-sans">
              {snippet}
            </p>
          </div>
        </div>

        {/* Structured badges count */}
        <div className="flex flex-wrap items-center gap-1.5 mb-4 text-[11px]">
          {measurementsCount > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-950/40 text-amber-300 border border-amber-800/30">
              <Gauge className="w-3 h-3" />
              {measurementsCount} params
            </span>
          )}
          {tasksCount > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-950/40 text-emerald-300 border border-emerald-800/30">
              <CheckCircle2 className="w-3 h-3" />
              {tasksCount} tasks
            </span>
          )}
          {note.structured_data?.tags?.slice(0, 2).map((t, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-950/40 text-blue-300 border border-blue-800/30"
            >
              <Tag className="w-2.5 h-2.5" />
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 mt-auto">
        <span className="text-[11px] font-mono text-slate-500">
          {note.confidence ? `${Math.round(note.confidence * 100)}% conf` : "Draft OCR"}
        </span>

        <div className="flex items-center gap-2">
          {onDelete && (
            <button
              onClick={() => onDelete(note.id)}
              className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition"
              title="Delete Note"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          {note.verification_status === "NEEDS_REVIEW" ? (
            <Link
              to={`/notes/${note.id}/review`}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 transition"
            >
              <span>Review OCR</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <Link
              to={`/notes/${note.id}`}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 transition"
            >
              <span>View Detail</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};
