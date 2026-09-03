import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  UploadCloud,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  RefreshCw,
  Plus,
  Layers,
} from "lucide-react";
import type { HandwrittenNote, OCRMetrics } from "../types/notes";
import { fetchNotesApi, fetchNotesMetricsApi, deleteNoteApi } from "../services/notesApi";
import { NoteCard } from "../components/notes/NoteCard";

export const HandwrittenNotesPage: React.FC = () => {
  const [notes, setNotes] = useState<HandwrittenNote[]>([]);
  const [metrics, setMetrics] = useState<OCRMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const loadData = async () => {
    setLoading(true);
    const [notesRes, metricsRes] = await Promise.all([
      fetchNotesApi({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        q: searchQuery || undefined,
      }),
      fetchNotesMetricsApi(),
    ]);

    setNotes(notesRes.notes);
    if (metricsRes) setMetrics(metricsRes);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  const handleDelete = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this handwritten note?")) {
      const ok = await deleteNoteApi(id);
      if (ok) {
        setNotes((prev) => prev.filter((n) => n.id !== id));
        loadData();
      }
    }
  };

  const getGlassCardStyle = (rgb: string) => ({
    background: `radial-gradient(circle at 85% 15%, rgba(${rgb}, 0.15), rgba(${rgb}, 0.05) 40%, rgba(8, 9, 11, 0.65) 90%)`,
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    border: `1px solid rgba(${rgb}, 0.3)`,
    boxShadow: `0 8px 32px rgba(0,0,0,0.4), 0 0 15px rgba(${rgb}, 0.12), inset 0 0 20px rgba(${rgb}, 0.05)`,
    borderRadius: "16px",
    transition: "all 220ms ease-out",
  });

  const getGlassCardHoverStyle = (rgb: string) => ({
    background: `radial-gradient(circle at 85% 15%, rgba(${rgb}, 0.22), rgba(${rgb}, 0.08) 50%, rgba(12, 13, 16, 0.75) 90%)`,
    borderColor: `rgba(${rgb}, 0.7)`,
    boxShadow: `0 12px 40px rgba(0,0,0,0.5), 0 0 25px rgba(${rgb}, 0.3), inset 0 0 30px rgba(${rgb}, 0.15)`,
    transform: "translateY(-3px) scale(1.015)",
  });

  return (
    <div 
      className="min-h-screen text-[#F2F2F2] pb-12 relative overflow-hidden"
      style={{ backgroundColor: "#040506", fontFamily: "'Space Grotesk', 'Inter', sans-serif" }}
    >
      {/* Subtle ambient lighting */}
      <div className="absolute top-[5%] left-[5%] w-[50%] h-[50%] rounded-full opacity-[0.06] blur-[160px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF7A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[10%] right-[5%] w-[40%] h-[40%] rounded-full opacity-[0.05] blur-[160px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF7A00 0%, transparent 70%)" }}></div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-[24px] pt-[24px] space-y-[24px]">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b relative" style={{ borderColor: "rgba(255,122,0,0.15)" }}>
          <div className="absolute top-0 left-0 w-full h-[150%] rounded-full opacity-[0.03] blur-[80px] pointer-events-none" style={{ background: "#FF7A00" }}></div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-[6px] text-[10px] font-[700] uppercase tracking-wider" style={{ background: "rgba(255,122,0,0.15)", border: "1px solid rgba(255,122,0,0.4)", color: "#FF9A3D", boxShadow: "0 0 10px rgba(255,122,0,0.2)" }}>
                SIH 2026 PS121
              </span>
              <span className="text-[11px] text-[#A1A1AA] font-['Inter',sans-serif] font-[500]">• Production Ingestion Pipeline</span>
            </div>
            <h1 className="text-[22px] sm:text-[28px] font-[700] text-white tracking-wider flex items-center gap-3">
              <FileText className="w-7 h-7 text-[#FF7A00] drop-shadow-[0_0_12px_rgba(255,122,0,0.5)]" />
              HANDWRITTEN NOTES & DOCUMENT OCR
            </h1>
            <p className="text-[13px] text-[#A1A1AA] mt-1.5 font-['Inter',sans-serif] max-w-2xl">
              Convert handwritten drilling logs, shift notes, and inspection sheets into verified, structured data using advanced optical character recognition.
            </p>
          </div>

          <div className="flex items-center gap-3 relative z-10">
            <button
              onClick={() => loadData()}
              className="p-[10px] rounded-[10px] transition-all group"
              style={{ background: "rgba(10,11,13,0.6)", border: "1px solid rgba(255,255,255,0.1)", backdropFilter: "blur(10px)" }}
              onMouseEnter={(e) => { 
                e.currentTarget.style.borderColor = "rgba(255,122,0,0.5)"; 
                e.currentTarget.style.background = "rgba(255,122,0,0.1)"; 
                e.currentTarget.style.boxShadow = "0 0 15px rgba(255,122,0,0.2)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => { 
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)"; 
                e.currentTarget.style.background = "rgba(10,11,13,0.6)"; 
                e.currentTarget.style.boxShadow = "none";
                e.currentTarget.style.transform = "none";
              }}
              title="Refresh notes list"
            >
              <RefreshCw className={`w-4 h-4 text-[#A1A1AA] group-hover:text-[#FF9A3D] ${loading ? "animate-spin text-[#FF7A00]" : ""}`} />
            </button>
            <Link
              to="/notes/upload"
              className="inline-flex items-center gap-2 px-[22px] py-[10px] rounded-[10px] font-[700] text-[12px] tracking-wide text-white transition-all group"
              style={{
                background: "radial-gradient(circle at top right, rgba(255,122,0,0.25), rgba(255,122,0,0.15) 70%)",
                border: "1px solid rgba(255,122,0,0.6)",
                boxShadow: "0 4px 15px rgba(0,0,0,0.3), 0 0 20px rgba(255,122,0,0.25), inset 0 0 10px rgba(255,122,0,0.2)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "radial-gradient(circle at top right, rgba(255,122,0,0.35), rgba(255,122,0,0.2) 70%)";
                e.currentTarget.style.borderColor = "#FFA85C";
                e.currentTarget.style.boxShadow = "0 8px 25px rgba(0,0,0,0.4), 0 0 30px rgba(255,122,0,0.4), inset 0 0 20px rgba(255,122,0,0.3)";
                e.currentTarget.style.transform = "translateY(-2px) scale(1.02)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "radial-gradient(circle at top right, rgba(255,122,0,0.25), rgba(255,122,0,0.15) 70%)";
                e.currentTarget.style.borderColor = "rgba(255,122,0,0.6)";
                e.currentTarget.style.boxShadow = "0 4px 15px rgba(0,0,0,0.3), 0 0 20px rgba(255,122,0,0.25), inset 0 0 10px rgba(255,122,0,0.2)";
                e.currentTarget.style.transform = "none";
              }}
            >
              <Plus className="w-4 h-4 text-white group-hover:brightness-125" />
              <span>Upload Handwritten Note</span>
            </Link>
          </div>
        </div>

        {/* Metrics Row */}
        {metrics && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-[20px]">
            {/* TOTAL NOTES (BLUE) */}
            <div 
              className="p-[18px] group cursor-default"
              style={getGlassCardStyle("59, 130, 246")}
              onMouseEnter={(e) => Object.assign(e.currentTarget.style, getGlassCardHoverStyle("59, 130, 246"))}
              onMouseLeave={(e) => Object.assign(e.currentTarget.style, getGlassCardStyle("59, 130, 246"))}
            >
              <div className="flex items-center justify-between text-[11px] font-[700] text-[#93C5FD] uppercase tracking-wider mb-3">
                <span className="drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]">Total Notes</span>
                <Layers className="w-4 h-4 text-[#60A5FA] group-hover:text-[#93C5FD] group-hover:drop-shadow-[0_0_10px_#60A5FA] transition-all" />
              </div>
              <div className="text-[32px] font-[700] text-white font-mono drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
                {metrics.total_notes}
              </div>
              <div className="text-[12px] text-[#94A3B8] mt-1 font-['Inter',sans-serif] font-[500]">Ingested in system</div>
            </div>

            {/* NEEDS REVIEW (AMBER) */}
            <div 
              className="p-[18px] group cursor-default"
              style={getGlassCardStyle("245, 158, 11")}
              onMouseEnter={(e) => Object.assign(e.currentTarget.style, getGlassCardHoverStyle("245, 158, 11"))}
              onMouseLeave={(e) => Object.assign(e.currentTarget.style, getGlassCardStyle("245, 158, 11"))}
            >
              <div className="flex items-center justify-between text-[11px] font-[700] text-[#FCD34D] uppercase tracking-wider mb-3">
                <span className="drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]">Needs Review</span>
                <Clock className="w-4 h-4 text-[#FBBF24] group-hover:text-[#FCD34D] group-hover:drop-shadow-[0_0_10px_#FBBF24] transition-all" />
              </div>
              <div className="text-[32px] font-[700] text-white font-mono drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
                {metrics.needs_review}
              </div>
              <div className="text-[12px] text-[#FDE68A] mt-1 font-['Inter',sans-serif] font-[500] opacity-80">Awaiting verification</div>
            </div>

            {/* VERIFIED DATA (GREEN) */}
            <div 
              className="p-[18px] group cursor-default"
              style={getGlassCardStyle("16, 185, 129")}
              onMouseEnter={(e) => Object.assign(e.currentTarget.style, getGlassCardHoverStyle("16, 185, 129"))}
              onMouseLeave={(e) => Object.assign(e.currentTarget.style, getGlassCardStyle("16, 185, 129"))}
            >
              <div className="flex items-center justify-between text-[11px] font-[700] text-[#6EE7B7] uppercase tracking-wider mb-3">
                <span className="drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]">Verified Data</span>
                <CheckCircle2 className="w-4 h-4 text-[#34D399] group-hover:text-[#6EE7B7] group-hover:drop-shadow-[0_0_10px_#34D399] transition-all" />
              </div>
              <div className="text-[32px] font-[700] text-white font-mono drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
                {metrics.verified}
              </div>
              <div className="text-[12px] text-[#A7F3D0] mt-1 font-['Inter',sans-serif] font-[500] opacity-80">
                {metrics.verification_rate_pct}% trust rate
              </div>
            </div>

            {/* PROCESSING (BLUE) */}
            <div 
              className="p-[18px] group cursor-default"
              style={getGlassCardStyle("59, 130, 246")}
              onMouseEnter={(e) => Object.assign(e.currentTarget.style, getGlassCardHoverStyle("59, 130, 246"))}
              onMouseLeave={(e) => Object.assign(e.currentTarget.style, getGlassCardStyle("59, 130, 246"))}
            >
              <div className="flex items-center justify-between text-[11px] font-[700] text-[#93C5FD] uppercase tracking-wider mb-3">
                <span className="drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]">Processing</span>
                <Loader2 className="w-4 h-4 text-[#60A5FA] animate-spin group-hover:text-[#93C5FD] group-hover:drop-shadow-[0_0_10px_#60A5FA]" />
              </div>
              <div className="text-[32px] font-[700] text-white font-mono drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
                {metrics.processing}
              </div>
              <div className="text-[12px] text-[#94A3B8] mt-1 font-['Inter',sans-serif] font-[500]">Active OCR jobs</div>
            </div>

            {/* OCR FAILED (RED) */}
            <div 
              className="p-[18px] group cursor-default"
              style={getGlassCardStyle("239, 68, 68")}
              onMouseEnter={(e) => Object.assign(e.currentTarget.style, getGlassCardHoverStyle("239, 68, 68"))}
              onMouseLeave={(e) => Object.assign(e.currentTarget.style, getGlassCardStyle("239, 68, 68"))}
            >
              <div className="flex items-center justify-between text-[11px] font-[700] text-[#FDA4AF] uppercase tracking-wider mb-3">
                <span className="drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]">OCR Failed</span>
                <AlertCircle className="w-4 h-4 text-[#F43F5E] group-hover:text-[#FDA4AF] group-hover:drop-shadow-[0_0_10px_#F43F5E] transition-all" />
              </div>
              <div className="text-[32px] font-[700] text-white font-mono drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
                {metrics.failed}
              </div>
              <div className="text-[12px] text-[#FECDD3] mt-1 font-['Inter',sans-serif] font-[500] opacity-80">Retry available</div>
            </div>
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div 
          className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-[16px] relative"
          style={{
            background: "radial-gradient(circle at left, rgba(255,122,0,0.08), rgba(8,9,11,0.65) 60%)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255,122,0,0.25)",
            boxShadow: "0 8px 30px rgba(0,0,0,0.3), inset 0 0 20px rgba(255,122,0,0.03)",
            borderRadius: "16px"
          }}
        >
          <div className="absolute top-1/2 left-1/4 w-[20%] h-[150%] rounded-full opacity-[0.05] blur-[40px] pointer-events-none -translate-y-1/2" style={{ background: "#FF7A00" }}></div>
          
          <form onSubmit={handleSearchSubmit} className="flex-1 relative group/search z-10">
            <Search className="w-5 h-5 text-[#A1A1AA] absolute left-[16px] top-1/2 -translate-y-1/2 group-focus-within/search:text-[#FF9A3D] transition-colors drop-shadow-sm" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search notes by keyword, equipment ID, parameters, or tags..."
              className="w-full pl-[46px] pr-[16px] py-[12px] rounded-[12px] text-[13px] text-white font-['Inter',sans-serif] font-[500] outline-none transition-all placeholder:text-[#686868]"
              style={{
                background: "rgba(0, 0, 0, 0.5)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
              onFocus={(e) => {
                e.currentTarget.style.background = "rgba(255,122,0,0.03)";
                e.currentTarget.style.borderColor = "rgba(255,122,0,0.5)";
                e.currentTarget.style.boxShadow = "0 0 15px rgba(255,122,0,0.2), inset 0 0 10px rgba(255,122,0,0.05)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.background = "rgba(0, 0, 0, 0.5)";
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
          </form>

          <div className="flex items-center gap-[10px] overflow-x-auto z-10">
            {["ALL", "NEEDS_REVIEW", "VERIFIED", "FAILED"].map((st) => {
              const isSelected = statusFilter === st;
              return (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className="px-[18px] py-[10px] rounded-[12px] text-[11px] font-[700] tracking-wider whitespace-nowrap transition-all"
                  style={
                    isSelected
                      ? {
                          background: "radial-gradient(circle at top, rgba(255,122,0,0.25), rgba(255,122,0,0.15))",
                          color: "#FFFFFF",
                          border: "1px solid rgba(255, 122, 0, 0.6)",
                          boxShadow: "0 4px 15px rgba(255, 122, 0, 0.2), inset 0 0 15px rgba(255,122,0,0.2)",
                          textShadow: "0 0 8px rgba(255,122,0,0.5)"
                        }
                      : {
                          background: "rgba(20, 20, 20, 0.4)",
                          color: "#A1A1AA",
                          border: "1px solid rgba(255, 255, 255, 0.1)",
                          boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
                        }
                  }
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = "rgba(255, 122, 0, 0.08)";
                      e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.3)";
                      e.currentTarget.style.color = "#FF9A3D";
                      e.currentTarget.style.boxShadow = "0 4px 12px rgba(255,122,0,0.1)";
                      e.currentTarget.style.transform = "translateY(-1px)";
                    } else {
                      e.currentTarget.style.background = "radial-gradient(circle at top, rgba(255,122,0,0.35), rgba(255,122,0,0.2))";
                      e.currentTarget.style.boxShadow = "0 6px 20px rgba(255, 122, 0, 0.3), inset 0 0 20px rgba(255,122,0,0.3)";
                      e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = "rgba(20, 20, 20, 0.4)";
                      e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)";
                      e.currentTarget.style.color = "#A1A1AA";
                      e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
                      e.currentTarget.style.transform = "none";
                    } else {
                      e.currentTarget.style.background = "radial-gradient(circle at top, rgba(255,122,0,0.25), rgba(255,122,0,0.15))";
                      e.currentTarget.style.boxShadow = "0 4px 15px rgba(255, 122, 0, 0.2), inset 0 0 15px rgba(255,122,0,0.2)";
                      e.currentTarget.style.transform = "none";
                    }
                  }}
                >
                  {st === "ALL" ? "All Notes" : st.replace("_", " ")}
                </button>
              );
            })}
          </div>
        </div>

        {/* Notes Grid */}
        {loading ? (
          <div className="py-[100px] text-center space-y-4">
            <Loader2 className="w-10 h-10 animate-spin text-[#FF7A00] mx-auto drop-shadow-[0_0_15px_rgba(255,122,0,0.5)]" />
            <p className="text-[13px] text-[#A1A1AA] font-mono tracking-widest uppercase">Loading OCR repository...</p>
          </div>
        ) : notes.length === 0 ? (
          <div 
            className="text-center space-y-[24px] py-[100px] transition-all duration-300 relative"
            style={{
              background: "radial-gradient(circle at center, rgba(255,122,0,0.08), rgba(10, 11, 13, 0.6) 70%)",
              backdropFilter: "blur(24px)",
              WebkitBackdropFilter: "blur(24px)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
              borderRadius: "24px",
              boxShadow: "inset 0 0 80px rgba(255,122,0,0.05), 0 30px 60px rgba(0,0,0,0.5)"
            }}
          >
            <div className="absolute inset-0 rounded-[24px] pointer-events-none" style={{ boxShadow: "inset 0 1px 1px rgba(255,255,255,0.05)" }}></div>
            
            <div 
              className="w-[90px] h-[90px] rounded-full flex items-center justify-center mx-auto transition-transform duration-500 hover:scale-110"
              style={{
                background: "radial-gradient(circle, rgba(255, 122, 0, 0.2), rgba(255, 122, 0, 0.05))",
                border: "1px solid rgba(255, 122, 0, 0.4)",
                boxShadow: "0 0 40px rgba(255, 122, 0, 0.25), inset 0 0 20px rgba(255,122,0,0.2)"
              }}
            >
              <UploadCloud className="w-[36px] h-[36px] text-[#FF9A3D] drop-shadow-[0_0_10px_rgba(255,122,0,0.6)]" />
            </div>
            
            <div className="relative z-10">
              <h3 className="text-[20px] font-[700] text-white tracking-wider drop-shadow-md">No handwritten notes found</h3>
              <p className="text-[14px] text-[#A1A1AA] max-w-md mx-auto mt-3 font-['Inter',sans-serif] leading-relaxed">
                {searchQuery
                  ? `No notes matched the query "${searchQuery}". Try different keywords.`
                  : "Upload a photograph or scan of field notes to start OCR extraction and verification."}
              </p>
            </div>

            <Link
              to="/notes/upload"
              className="inline-flex items-center gap-2 px-[28px] py-[14px] text-[14px] font-[700] text-white rounded-[12px] transition-all group tracking-wide mt-6 relative z-10"
              style={{
                background: "radial-gradient(circle at top, rgba(255,122,0,0.25), rgba(255,122,0,0.15))",
                border: "1px solid rgba(255, 122, 0, 0.6)",
                boxShadow: "0 8px 25px rgba(255, 122, 0, 0.3), inset 0 0 15px rgba(255, 122, 0, 0.2)",
                textShadow: "0 0 10px rgba(255,122,0,0.4)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "radial-gradient(circle at top, rgba(255,122,0,0.35), rgba(255,122,0,0.2))";
                e.currentTarget.style.borderColor = "#FFA85C";
                e.currentTarget.style.boxShadow = "0 12px 35px rgba(255, 122, 0, 0.5), 0 0 40px rgba(255,122,0,0.3), inset 0 0 25px rgba(255, 122, 0, 0.3)";
                e.currentTarget.style.transform = "translateY(-3px) scale(1.025)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "radial-gradient(circle at top, rgba(255,122,0,0.25), rgba(255,122,0,0.15))";
                e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.6)";
                e.currentTarget.style.boxShadow = "0 8px 25px rgba(255, 122, 0, 0.3), inset 0 0 15px rgba(255, 122, 0, 0.2)";
                e.currentTarget.style.transform = "none";
              }}
            >
              <Plus className="w-5 h-5 text-white group-hover:brightness-125 drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" />
              UPLOAD FIRST NOTE
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-[24px]">
            {notes.map((note) => (
              <NoteCard key={note.id} note={note} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
