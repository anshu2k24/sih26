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
    <div 
      className="flex flex-col justify-between rounded-[20px] p-[24px] transition-all duration-300 group relative"
      style={{
        background: "radial-gradient(circle at top left, rgba(255,122,0,0.06), rgba(8,9,11,0.7) 70%)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        boxShadow: "0 8px 30px rgba(0,0,0,0.3), inset 0 0 20px rgba(255,122,0,0.02)",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "radial-gradient(circle at top left, rgba(255,122,0,0.12), rgba(10,12,14,0.75) 80%)";
        e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.5)";
        e.currentTarget.style.boxShadow = "0 12px 40px rgba(0,0,0,0.4), 0 0 25px rgba(255,122,0,0.2), inset 0 0 30px rgba(255,122,0,0.1)";
        e.currentTarget.style.transform = "translateY(-3px) scale(1.015)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "radial-gradient(circle at top left, rgba(255,122,0,0.06), rgba(8,9,11,0.7) 70%)";
        e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.08)";
        e.currentTarget.style.boxShadow = "0 8px 30px rgba(0,0,0,0.3), inset 0 0 20px rgba(255,122,0,0.02)";
        e.currentTarget.style.transform = "none";
      }}
    >
      <div>
        {/* Header: Title & Badges */}
        <div className="flex items-start justify-between gap-3 mb-[20px]">
          <div className="flex-1 min-w-0">
            <h3 className="text-[16px] font-[700] text-white tracking-wide truncate group-hover:text-[#FF9A3D] group-hover:drop-shadow-[0_0_8px_rgba(255,122,0,0.4)] transition-all">
              {note.title}
            </h3>
            <div className="flex items-center gap-[10px] text-[12px] text-[#A1A1AA] mt-1.5 font-mono">
              <span className="flex items-center gap-1.5 font-[500]">
                <Calendar className="w-3.5 h-3.5 text-[#686868] group-hover:text-[#FF7A00] transition-colors" />
                {new Date(note.created_at).toLocaleDateString()}
              </span>
              {note.structured_data?.date && (
                <span className="text-[#60A5FA] font-[700] tracking-wider drop-shadow-[0_0_5px_rgba(59,130,246,0.3)]">
                  • {note.structured_data.date}
                </span>
              )}
            </div>
          </div>
          <NoteStatusBadge
            verificationStatus={note.verification_status}
            ocrStatus={note.ocr_status}
            size="md"
          />
        </div>

        {/* Thumbnail + Excerpt */}
        <div className="flex gap-[20px] mb-[24px]">
          {imageUrl ? (
            <div 
              className="w-[90px] h-[90px] rounded-[16px] overflow-hidden shrink-0 relative"
              style={{ background: "rgba(0,0,0,0.8)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 4px 15px rgba(0,0,0,0.5)" }}
            >
              <div className="absolute inset-0 bg-[#FF7A00] opacity-0 group-hover:opacity-10 transition-opacity duration-300 z-10 pointer-events-none"></div>
              <img
                src={imageUrl}
                alt={note.title}
                className="w-full h-full object-cover group-hover:scale-110 transition duration-500 opacity-90 group-hover:opacity-100 relative z-0"
              />
            </div>
          ) : (
            <div 
              className="w-[90px] h-[90px] rounded-[16px] shrink-0 flex items-center justify-center transition-all duration-300"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)", boxShadow: "inset 0 0 20px rgba(0,0,0,0.5)" }}
            >
              <FileText className="w-8 h-8 text-[#686868] group-hover:text-[#FF7A00] group-hover:drop-shadow-[0_0_10px_rgba(255,122,0,0.5)] transition-all" />
            </div>
          )}

          <div className="flex-1 min-w-0">
            <p className="text-[13px] text-[#A1A1AA] line-clamp-3 leading-relaxed font-['Inter',sans-serif] font-[500] group-hover:text-[#F2F2F2] transition-colors">
              {snippet}
            </p>
          </div>
        </div>

        {/* Structured badges count */}
        <div className="flex flex-wrap items-center gap-[10px] mb-[24px] text-[11px] font-[700] tracking-wider uppercase">
          {measurementsCount > 0 && (
            <span 
              className="inline-flex items-center gap-1.5 px-[10px] py-[6px] rounded-[8px]"
              style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)", color: "#FBBF24", boxShadow: "0 0 10px rgba(245,158,11,0.1)" }}
            >
              <Gauge className="w-3.5 h-3.5" />
              {measurementsCount} param
            </span>
          )}
          {tasksCount > 0 && (
            <span 
              className="inline-flex items-center gap-1.5 px-[10px] py-[6px] rounded-[8px]"
              style={{ background: "rgba(16,185,129,0.12)", border: "1px solid rgba(16,185,129,0.3)", color: "#34D399", boxShadow: "0 0 10px rgba(16,185,129,0.1)" }}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {tasksCount} tasks
            </span>
          )}
          {note.structured_data?.tags?.slice(0, 2).map((t, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 px-[10px] py-[6px] rounded-[8px]"
              style={{ background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.3)", color: "#60A5FA", boxShadow: "0 0 10px rgba(59,130,246,0.1)" }}
            >
              <Tag className="w-3 h-3" />
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="flex items-center justify-between pt-[20px] mt-auto" style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <span className="text-[12px] font-mono font-[700] text-[#686868] tracking-widest group-hover:text-[#A1A1AA] transition-colors">
          {note.confidence ? `CONF: ${(note.confidence * 100).toFixed(0)}%` : "DRAFT OCR"}
        </span>

        <div className="flex items-center gap-[12px]">
          {onDelete && (
            <button
              onClick={() => onDelete(note.id)}
              className="p-[8px] rounded-[10px] transition-all text-[#686868]"
              style={{ background: "rgba(255,255,255,0.02)", border: "1px solid transparent" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(225, 29, 72, 0.15)";
                e.currentTarget.style.borderColor = "rgba(225, 29, 72, 0.4)";
                e.currentTarget.style.color = "#FB7185";
                e.currentTarget.style.boxShadow = "0 0 15px rgba(225,29,72,0.2)";
                e.currentTarget.style.transform = "scale(1.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.02)";
                e.currentTarget.style.borderColor = "transparent";
                e.currentTarget.style.color = "#686868";
                e.currentTarget.style.boxShadow = "none";
                e.currentTarget.style.transform = "none";
              }}
              title="Delete Note"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          {note.verification_status === "NEEDS_REVIEW" ? (
            <Link
              to={`/notes/${note.id}/review`}
              className="inline-flex items-center gap-2 px-[16px] py-[8px] text-[12px] font-[700] uppercase tracking-wider rounded-[10px] transition-all"
              style={{
                background: "radial-gradient(circle at top, rgba(245,158,11,0.25), rgba(245,158,11,0.15))",
                border: "1px solid rgba(245, 158, 11, 0.5)",
                color: "#FFFFFF",
                boxShadow: "0 4px 15px rgba(245, 158, 11, 0.2), inset 0 0 10px rgba(245,158,11,0.2)",
                textShadow: "0 0 8px rgba(245,158,11,0.5)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "radial-gradient(circle at top, rgba(245,158,11,0.35), rgba(245,158,11,0.2))";
                e.currentTarget.style.borderColor = "#FCD34D";
                e.currentTarget.style.boxShadow = "0 8px 25px rgba(245, 158, 11, 0.4), 0 0 20px rgba(245,158,11,0.3), inset 0 0 15px rgba(245,158,11,0.3)";
                e.currentTarget.style.transform = "translateY(-2px) scale(1.02)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "radial-gradient(circle at top, rgba(245,158,11,0.25), rgba(245,158,11,0.15))";
                e.currentTarget.style.borderColor = "rgba(245, 158, 11, 0.5)";
                e.currentTarget.style.boxShadow = "0 4px 15px rgba(245, 158, 11, 0.2), inset 0 0 10px rgba(245,158,11,0.2)";
                e.currentTarget.style.transform = "none";
              }}
            >
              <span>Review OCR</span>
              <ChevronRight className="w-4 h-4 text-[#FDE68A]" />
            </Link>
          ) : (
            <Link
              to={`/notes/${note.id}`}
              className="inline-flex items-center gap-2 px-[16px] py-[8px] text-[12px] font-[700] uppercase tracking-wider rounded-[10px] transition-all text-white"
              style={{
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                backdropFilter: "blur(10px)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "radial-gradient(circle at top, rgba(255,122,0,0.15), rgba(255,122,0,0.05))";
                e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.5)";
                e.currentTarget.style.boxShadow = "0 6px 20px rgba(255, 122, 0, 0.25), inset 0 0 15px rgba(255,122,0,0.1)";
                e.currentTarget.style.transform = "translateY(-2px) scale(1.02)";
                e.currentTarget.style.textShadow = "0 0 8px rgba(255,122,0,0.4)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.03)";
                e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)";
                e.currentTarget.style.boxShadow = "none";
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.textShadow = "none";
              }}
            >
              <span>View Detail</span>
              <ChevronRight className="w-4 h-4 text-[#FF7A00]" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};
