/**
 * RAG Search Page
 * ================
 * Hybrid search + optional AI Q&A interface for the PS121 RAG module.
 *
 * STANDALONE PAGE — does not modify any existing pages.
 * Mount at route /rag in App.tsx (see docs/integration.md).
 *
 * Features:
 * - Hybrid search (semantic + keyword + metadata)
 * - Metadata filters (date range, tags, identifiers)
 * - Full provenance display (note → OCR run → image)
 * - AI Q&A mode with source citations
 * - RAG health status indicator
 */

import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  Search,
  Brain,
  Tag,
  Calendar,
  Fingerprint,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Activity,
  Zap,
  BookOpen,
  Link,
  BarChart3,
  X,
  Send,
  Info,
  RefreshCw,
  Shield,
} from "lucide-react";
import {
  ragSearch,
  ragQuery,
  getRAGHealth,
  type SearchResult,
  type SourceCitation,
  type SearchFilters,
  type RAGHealth,
} from "../services/ragApi";

// ── Types ─────────────────────────────────────────────────────────────────

type Mode = "search" | "qa";
type SearchMode = "hybrid" | "semantic" | "keyword" | "metadata";

interface SearchState {
  query: string;
  mode: SearchMode;
  filters: SearchFilters;
  tags: string;
  identifiers: string;
  dateFrom: string;
  dateTo: string;
  topK: number;
}

interface ResultsState {
  results: SearchResult[];
  duration_ms: number | null;
  query: string;
  mode: string;
}

interface QAState {
  question: string;
  answer: string | null;
  sources: SourceCitation[];
  llm_used: boolean;
  insufficient: boolean;
  duration_ms: number | null;
  retrieval_count: number;
}

// ── Sub-Components ────────────────────────────────────────────────────────

function HealthBadge({ health }: { health: RAGHealth | null }) {
  if (!health) return null;
  const ok = health.status === "HEALTHY";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-mono font-bold border shadow-[0_0_10px_rgba(255,140,0,0.15)] ${
        ok
          ? "bg-[rgba(10,10,10,0.6)] text-emerald-400 border-emerald-500/30"
          : "bg-[rgba(10,10,10,0.6)] text-[#FF9D1A] border-[#FF9D1A]/30"
      }`}
      style={{ backdropFilter: "blur(8px)" }}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? "bg-emerald-400 animate-pulse" : "bg-[#FF9D1A] shadow-[0_0_8px_#FF9D1A]"}`} />
      {health.status}
    </span>
  );
}

function ScoreBar({ score, label, color }: { score: number | null; label: string; color: string }) {
  if (score === null || score === undefined) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-500 font-mono w-14 shrink-0">{label}</span>
      <div className="flex-1 bg-slate-800 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full ${color} transition-all duration-500`}
          style={{ width: `${Math.min(100, score * 100)}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-slate-400 w-10 text-right">
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
}

function ProvenancePanel({ result }: { result: SearchResult }) {
  const [open, setOpen] = useState(false);
  const prov = result.provenance;

  return (
    <div className="mt-3 border-t border-slate-800/60 pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-slate-300 font-mono transition-colors"
      >
        <Link className="w-3 h-3" />
        PROVENANCE
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && prov && (
        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
          {[
            ["NOTE ID", prov.note_id?.slice(0, 8) + "..."],
            ["CHUNK ID", prov.chunk_id?.slice(0, 8) + "..."],
            ["VERIFIED BY", prov.verified_by || "—"],
            ["VERIFIED AT", prov.verified_at ? new Date(prov.verified_at).toLocaleDateString() : "—"],
            ["SOURCE FILE", prov.source_file_id?.slice(0, 12) + "..." || "—"],
            ["OCR RUN", prov.ocr_run_id?.slice(0, 8) + "..." || "—"],
            ["VERSION", String(prov.version)],
            ["STATUS", prov.verification_status],
          ].map(([k, v]) => (
            <div key={k} className="flex gap-2">
              <span className="text-slate-600 w-20 shrink-0">{k}</span>
              <span className="text-slate-400 truncate">{v}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ResultCard({ result, index }: { result: SearchResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = result.text.length > 280;
  const displayText = isLong && !expanded ? result.text.slice(0, 280) + "…" : result.text;

  const sectionColor: Record<string, string> = {
    observations: "text-amber-400 bg-amber-950/40 border-amber-500/20",
    measurements: "text-[#FF9D1A] bg-[#FF9D1A]/10 border-[#FF9D1A]/20",
    tasks: "text-amber-400 bg-amber-950/40 border-amber-500/20",
    entities: "text-amber-500 bg-amber-950/40 border-amber-500/20",
    title: "text-[#FF9D1A] bg-[#FF9D1A]/10 border-[#FF9D1A]/20",
    summary: "text-[#FFB000] bg-[#FFB000]/10 border-[#FFB000]/20",
    body: "text-slate-400 bg-[rgba(10,10,10,0.5)] border-slate-700/20",
  };
  const sectionStyle = sectionColor[result.section] || sectionColor.body;

  return (
    <div 
      className="rounded-2xl p-4 transition-all group"
      style={{ 
        background: "rgba(15, 10, 5, 0.4)", 
        border: "1px solid rgba(255, 140, 0, 0.15)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.02)",
        backdropFilter: "blur(12px)"
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 w-6 h-6 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 text-[10px] font-mono font-bold flex items-center justify-center">
            {index + 1}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-bold text-white font-mono truncate">{result.title}</p>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border ${sectionStyle}`}>
              {result.section.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Score badge */}
        <div className="flex-shrink-0 flex flex-col items-end gap-1">
          <div className="px-2 py-1 rounded-lg" style={{ background: "rgba(255,140,0,0.1)", border: "1px solid rgba(255,140,0,0.25)" }}>
            <span className="text-[#FF9D1A] font-mono font-bold text-sm">
              {(result.score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Content */}
      <p className="text-sm text-slate-300 leading-relaxed font-mono whitespace-pre-line">
        {displayText}
      </p>
      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-1 text-[11px] text-[#FF9D1A] hover:text-[#FFB000] font-mono transition-colors"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}

      {/* Score breakdown */}
      {result.score_breakdown && (
        <div className="mt-3 space-y-1">
          <ScoreBar score={result.score_breakdown.semantic} label="SEMANTIC" color="bg-[#FF9D1A]" />
          <ScoreBar score={result.score_breakdown.keyword} label="KEYWORD" color="bg-[#FFB000]" />
        </div>
      )}

      {/* Metadata tags */}
      {Array.isArray(result.metadata?.tags) && result.metadata.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {(result.metadata.tags as string[]).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded-full text-[10px] font-mono text-slate-400"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <ProvenancePanel result={result} />
    </div>
  );
}

function QASourceCard({ source }: { source: SourceCitation }) {
  return (
    <div 
      className="rounded-xl p-3"
      style={{
        background: "rgba(15, 10, 5, 0.4)",
        border: "1px solid rgba(255, 140, 0, 0.15)",
        boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
      }}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <span className="w-5 h-5 rounded-lg text-[#FF9D1A] text-[10px] font-mono font-bold flex items-center justify-center" style={{ background: "rgba(255,140,0,0.1)", border: "1px solid rgba(255,140,0,0.25)" }}>
            {source.citation_index}
          </span>
          <span className="text-xs font-bold text-white font-mono truncate max-w-[180px]">
            {source.title}
          </span>
        </div>
        <span className="text-[10px] font-mono text-[#FF9D1A] px-1.5 py-0.5 rounded-md" style={{ background: "rgba(255,140,0,0.1)", border: "1px solid rgba(255,140,0,0.2)" }}>
          {(source.relevance_score * 100).toFixed(0)}%
        </span>
      </div>
      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
        {source.section}
      </span>
      {source.text_preview && (
        <p className="mt-1.5 text-[11px] text-slate-400 font-mono leading-relaxed line-clamp-2">
          {source.text_preview}
        </p>
      )}
      <div className="flex gap-3 mt-2 text-[10px] font-mono text-slate-600">
        {source.verified_at && (
          <span>{new Date(source.verified_at).toLocaleDateString()}</span>
        )}
        {source.verified_by && <span>by {source.verified_by}</span>}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────

export const RAGSearchPage: React.FC = () => {
  const [mode, setMode] = useState<Mode>("search");
  const [health, setHealth] = useState<RAGHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const [searchState, setSearchState] = useState<SearchState>({
    query: "",
    mode: "hybrid",
    filters: {},
    tags: "",
    identifiers: "",
    dateFrom: "",
    dateTo: "",
    topK: 10,
  });

  const [results, setResults] = useState<ResultsState | null>(null);
  const [qa, setQA] = useState<QAState>({
    question: "",
    answer: null,
    sources: [],
    llm_used: false,
    insufficient: false,
    duration_ms: null,
    retrieval_count: 0,
  });

  const inputRef = useRef<HTMLInputElement>(null);
  const qaRef = useRef<HTMLTextAreaElement>(null);

  // Load health on mount
  useEffect(() => {
    getRAGHealth()
      .then(setHealth)
      .catch(() => {});
  }, []);

  const buildFilters = (): SearchFilters => {
    const f: SearchFilters = {};
    if (searchState.dateFrom) f.date_from = searchState.dateFrom;
    if (searchState.dateTo) f.date_to = searchState.dateTo;
    if (searchState.tags.trim()) {
      f.tags = searchState.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
    }
    if (searchState.identifiers.trim()) {
      f.identifiers = searchState.identifiers
        .split(",")
        .map((i) => i.trim())
        .filter(Boolean);
    }
    return f;
  };

  const handleSearch = useCallback(async () => {
    if (!searchState.query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await ragSearch({
        query: searchState.query,
        top_k: searchState.topK,
        mode: searchState.mode,
        filters: buildFilters(),
      });
      setResults({
        results: res.results,
        duration_ms: res.duration_ms,
        query: res.query,
        mode: res.mode,
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [searchState]);

  const handleQA = useCallback(async () => {
    if (!qa.question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await ragQuery({
        question: qa.question,
        top_k: searchState.topK,
        filters: buildFilters(),
      });
      setQA((prev) => ({
        ...prev,
        answer: res.answer,
        sources: res.sources,
        llm_used: res.llm_used,
        insufficient: res.insufficient_information,
        duration_ms: res.duration_ms,
        retrieval_count: res.retrieval_count ?? res.sources.length,
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [qa.question, searchState.topK]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      mode === "search" ? handleSearch() : handleQA();
    }
  };

  const modeButtons: { id: SearchMode; label: string; icon: React.ReactNode }[] = [
    { id: "hybrid", label: "Hybrid", icon: <Zap className="w-3 h-3" /> },
    { id: "semantic", label: "Semantic", icon: <Brain className="w-3 h-3" /> },
    { id: "keyword", label: "Keyword", icon: <Search className="w-3 h-3" /> },
    { id: "metadata", label: "Metadata", icon: <Tag className="w-3 h-3" /> },
  ];

  return (
    <div 
      className="min-h-screen relative text-white font-mono pb-12"
      style={{ 
        backgroundColor: "#050607", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-network-orange.png')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed"
      }}
    >
      <div className="relative z-10 max-w-6xl mx-auto px-6 pt-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 mb-2">
          <div className="flex items-start gap-4">
            <div>
              <h1 className="text-xl font-bold tracking-tight font-mono text-white mb-1 drop-shadow-sm">
                RAG INTELLIGENT SEARCH
              </h1>
              <p className="text-[11px] text-slate-400 font-mono tracking-wide drop-shadow-sm">
                PS121 <span className="text-[#FF9D1A] mx-1">•</span> Verified Documents Only <span className="text-[#FF9D1A] mx-1">•</span> Hybrid Semantic + Keyword
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => getRAGHealth().then(setHealth).catch(() => {})}
              className="p-2 text-[#FF9D1A]/70 hover:text-[#FF9D1A] hover:bg-[#FF9D1A]/10 rounded-lg transition-all"
              title="Refresh health"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mode Tabs */}
        <div className="flex gap-3 mb-6">
          {(["search", "qa"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              id={`rag-mode-${m}`}
              onClick={() => setMode(m)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-mono font-bold border transition-all ${
                mode === m
                  ? "bg-[#FF9D1A]/10 text-white border-[#FF9D1A] shadow-[0_0_15px_rgba(255,140,0,0.3)] transform -translate-y-[1px]"
                  : "bg-transparent text-slate-400 border-slate-700/50 hover:border-[#FF9D1A]/50 hover:text-white hover:bg-[#FF9D1A]/5 hover:shadow-[0_0_10px_rgba(255,140,0,0.1)] hover:-translate-y-[1px]"
              }`}
              style={{ backdropFilter: mode === m ? "blur(8px)" : "none" }}
            >
              {m === "search" ? (
                <><Search className={`w-4 h-4 ${mode === m ? "text-[#FF9D1A]" : ""}`} /> HYBRID SEARCH</>
              ) : (
                <><BookOpen className={`w-4 h-4 ${mode === m ? "text-[#FF9D1A]" : ""}`} /> AI Q&A</>
              )}
            </button>
          ))}
        </div>

        {/* Search / QA Input Panel */}
        <div 
          className="rounded-2xl p-6 mb-8 transition-all"
          style={{
            background: "rgba(15, 10, 5, 0.65)",
            backdropFilter: "blur(18px) saturate(120%)",
            border: "1px solid rgba(255, 140, 0, 0.3)",
            boxShadow: "0 8px 35px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.035)",
          }}
        >
          {mode === "search" ? (
            <>
              {/* Search mode controls */}
              <div className="flex gap-2 mb-4">
                {modeButtons.map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    id={`rag-search-mode-${b.id}`}
                    onClick={() => setSearchState((s) => ({ ...s, mode: b.id }))}
                    className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-[11px] font-mono font-bold border transition-all ${
                      searchState.mode === b.id
                        ? "bg-[rgba(255,140,0,0.1)] text-white border-[#FF9D1A] shadow-[0_0_15px_rgba(255,140,0,0.25)]"
                        : "text-slate-500 border-slate-700/50 hover:border-[#FF9D1A]/50 hover:text-[#FF9D1A] hover:shadow-[0_0_10px_rgba(255,140,0,0.15)] bg-[rgba(10,10,10,0.4)]"
                    }`}
                  >
                    {React.cloneElement(b.icon as React.ReactElement<any>, { className: `w-3.5 h-3.5 ${searchState.mode === b.id ? "text-[#FF9D1A]" : ""}` })}
                    {b.label}
                  </button>
                ))}
              </div>

              <div className="relative group">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#FF9D1A] transition-all group-focus-within:text-[#FFB000]" />
                <input
                  ref={inputRef}
                  id="rag-search-input"
                  type="text"
                  placeholder="Search verified documents... e.g. 'pump vibration above threshold'"
                  value={searchState.query}
                  onChange={(e) => setSearchState((s) => ({ ...s, query: e.target.value }))}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-[rgba(5,5,5,0.5)] border border-[#FF9D1A]/40 rounded-xl pl-12 pr-4 py-4 text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:border-[#FF9D1A] focus:shadow-[0_0_20px_rgba(255,140,0,0.3)] transition-all"
                />
                {searchState.query && (
                  <button
                    type="button"
                    onClick={() => setSearchState((s) => ({ ...s, query: "" }))}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-[#FF9D1A]"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="relative group">
              <Brain className="absolute left-4 top-4 w-5 h-5 text-[#FF9D1A] transition-all group-focus-within:text-[#FFB000]" />
              <textarea
                ref={qaRef}
                id="rag-qa-input"
                placeholder="Ask a question about verified documents... e.g. 'What vibration issues were reported in August 2026?'"
                value={qa.question}
                onChange={(e) => setQA((prev) => ({ ...prev, question: e.target.value }))}
                onKeyDown={handleKeyDown}
                rows={3}
                className="w-full bg-[rgba(5,5,5,0.5)] border border-[#FF9D1A]/40 rounded-xl pl-12 pr-12 py-4 text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:border-[#FF9D1A] focus:shadow-[0_0_20px_rgba(255,140,0,0.3)] transition-all resize-none"
              />
              {!health?.llm_enabled && (
                <div className="mt-2 flex items-center gap-2 text-[11px] font-mono text-[#FF9D1A]">
                  <Info className="w-3 h-3 shrink-0" />
                  LLM disabled — search-only mode. Set RAG_LLM_ENABLED=true to enable AI answers.
                </div>
              )}
            </div>
          )}

          {/* Filters */}
          <div className="mt-4">
            <button
              type="button"
              id="rag-filters-toggle"
              onClick={() => setShowFilters((v) => !v)}
              className="flex items-center gap-1.5 text-[11px] font-mono text-[#FF9D1A]/70 hover:text-[#FF9D1A] transition-colors"
            >
              FILTERS
              {showFilters ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
              {(searchState.dateFrom || searchState.dateTo || searchState.tags || searchState.identifiers) && (
                <span className="w-1.5 h-1.5 rounded-full bg-[#FF9D1A]" />
              )}
            </button>

            {showFilters && (
              <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="block text-[10px] font-mono text-slate-500 mb-1.5 uppercase tracking-wider">
                    <Calendar className="inline w-3 h-3 mr-1" />Date From
                  </label>
                  <input
                    id="rag-filter-date-from"
                    type="date"
                    value={searchState.dateFrom}
                    onChange={(e) =>
                      setSearchState((s) => ({ ...s, dateFrom: e.target.value }))
                    }
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-blue-500/40"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-slate-500 mb-1.5 uppercase tracking-wider">
                    <Calendar className="inline w-3 h-3 mr-1" />Date To
                  </label>
                  <input
                    id="rag-filter-date-to"
                    type="date"
                    value={searchState.dateTo}
                    onChange={(e) =>
                      setSearchState((s) => ({ ...s, dateTo: e.target.value }))
                    }
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-blue-500/40"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-slate-500 mb-1.5 uppercase tracking-wider">
                    <Tag className="inline w-3 h-3 mr-1" />Tags (comma-sep)
                  </label>
                  <input
                    id="rag-filter-tags"
                    type="text"
                    placeholder="Maintenance, Vibration"
                    value={searchState.tags}
                    onChange={(e) =>
                      setSearchState((s) => ({ ...s, tags: e.target.value }))
                    }
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500/40"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-slate-500 mb-1.5 uppercase tracking-wider">
                    <Fingerprint className="inline w-3 h-3 mr-1" />Identifiers
                  </label>
                  <input
                    id="rag-filter-identifiers"
                    type="text"
                    placeholder="MUD-PUMP-008"
                    value={searchState.identifiers}
                    onChange={(e) =>
                      setSearchState((s) => ({
                        ...s,
                        identifiers: e.target.value,
                      }))
                    }
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500/40"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Action button */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <label className="text-[11px] font-mono text-[#FF9D1A]/70">
                TOP K:
              </label>
              <select
                id="rag-top-k"
                value={searchState.topK}
                onChange={(e) => setSearchState((s) => ({ ...s, topK: Number(e.target.value) }))}
                className="bg-[rgba(10,10,10,0.5)] border border-[#FF9D1A]/30 rounded-lg px-2 py-1.5 text-xs font-mono text-white focus:outline-none hover:border-[#FF9D1A]/50 transition-colors cursor-pointer"
              >
                {[5, 10, 20, 50].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
            <button
              id="rag-submit-btn"
              type="button"
              onClick={mode === "search" ? handleSearch : handleQA}
              disabled={loading || (mode === "search" ? !searchState.query.trim() : !qa.question.trim())}
              className="flex items-center gap-2 px-8 py-3 bg-[linear-gradient(135deg,rgba(255,140,0,0.95),rgba(255,100,0,1))] hover:bg-[linear-gradient(135deg,rgba(255,160,0,1),rgba(255,120,0,1))] disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-mono text-sm font-bold transition-all shadow-[0_0_25px_rgba(255,140,0,0.65)] hover:shadow-[0_0_40px_rgba(255,140,0,0.9)] hover:-translate-y-[1px] hover:scale-[1.02] active:scale-95 border border-[#FF9D1A]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : mode === "search" ? (
                <Search className="w-4 h-4" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              {loading ? "PROCESSING..." : mode === "search" ? "SEARCH" : "ASK"}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-3 bg-rose-950/40 border border-rose-500/30 rounded-xl p-4 mb-6 text-sm font-mono text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            {error}
          </div>
        )}

        {/* Search Results */}
        {mode === "search" && results && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-mono text-slate-400">
                  <span className="text-white font-bold">{results.results.length}</span>{" "}
                  results for{" "}
                  <span className="text-[#FF9D1A]">"{results.query}"</span>
                </span>
                <span className="text-[10px] font-mono text-slate-600 uppercase">
                  {results.mode}
                </span>
              </div>
              {results.duration_ms && (
                <span className="text-[11px] font-mono text-slate-600">
                  {results.duration_ms.toFixed(0)}ms
                </span>
              )}
            </div>

            {results.results.length === 0 ? (
              <div className="text-center py-16 text-slate-500 font-mono">
                <Search className="w-10 h-10 mx-auto mb-3 opacity-30 text-[#FF9D1A]" />
                <p className="text-sm text-slate-300">No results found.</p>
                <p className="text-xs mt-1 text-slate-600">
                  Try different keywords or verify the note has been indexed.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {results.results.map((r, i) => (
                  <ResultCard key={r.chunk_id} result={r} index={i} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Q&A Results */}
        {mode === "qa" && qa.answer !== null && (
          <div className="space-y-6">
            {/* Answer Panel */}
            <div
              className="rounded-2xl p-6"
              style={{
                background: qa.insufficient ? "rgba(255,140,0,0.05)" : "rgba(10,10,10,0.6)",
                border: qa.insufficient ? "1px solid rgba(255,140,0,0.3)" : "1px solid rgba(255,140,0,0.15)",
                backdropFilter: "blur(12px)"
              }}
            >
              <div className="flex items-center gap-2 mb-4">
                {qa.insufficient ? (
                  <AlertCircle className="w-4 h-4 text-[#FF9D1A]" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-[#FF9D1A]" />
                )}
                <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                  {qa.llm_used ? "AI ANSWER" : "SEARCH SUMMARY"}
                </span>
                {qa.llm_used && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono text-[#FF9D1A]" style={{ background: "rgba(255,140,0,0.1)", border: "1px solid rgba(255,140,0,0.3)" }}>
                    LLM
                  </span>
                )}
                {qa.duration_ms && (
                  <span className="ml-auto text-[10px] font-mono text-slate-500">
                    {qa.duration_ms.toFixed(0)}ms
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-200 font-mono leading-relaxed whitespace-pre-line">
                {qa.answer}
              </p>
              {!qa.insufficient && (
                <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-slate-500">
                  <Shield className="w-3 h-3 text-[#FF9D1A]" />
                  Answer derived from {qa.retrieval_count} verified document
                  {qa.retrieval_count !== 1 ? "s" : ""}
                </div>
              )}
            </div>

            {/* Sources */}
            {qa.sources.length > 0 && (
              <div>
                <h3 className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Link className="w-3.5 h-3.5" />
                  SOURCE CITATIONS ({qa.sources.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {qa.sources.map((s) => (
                    <QASourceCard key={`${s.note_id}-${s.chunk_id}`} source={s} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && !results && qa.answer === null && (
          <div className="text-center py-20">
            <div className="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center transition-all" style={{ background: "rgba(255,140,0,0.05)", border: "1px solid rgba(255,140,0,0.2)", boxShadow: "0 0 20px rgba(255,140,0,0.1)" }}>
              <Brain className="w-8 h-8 text-[#FF9D1A]" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RAGSearchPage;
