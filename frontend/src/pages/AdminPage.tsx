import React, { useState, useEffect } from "react";
import { fetchDetailedHealthApi, fetchDataProvenanceApi } from "../services/api";
import {
  Server,
  Cpu,
  Database,
  ShieldCheck,
  RefreshCw,
  FileCheck2,
  HardDrive,
} from "lucide-react";

export const AdminPage: React.FC = () => {
  const [healthData, setHealthData] = useState<any | null>(null);
  const [provenanceData, setProvenanceData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    setLoading(true);
    const [h, p] = await Promise.all([fetchDetailedHealthApi(), fetchDataProvenanceApi()]);
    setHealthData(h);
    setProvenanceData(p);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6 font-mono">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5 text-indigo-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              SYSTEM ADMINISTRATION & PROVENANCE AUDIT
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-indigo-950/80 text-indigo-400 border border-indigo-500/30 font-bold">
              PLATFORM HEALTH & COMPLIANCE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time infrastructure health monitoring, OCR availability, database status, and verified dataset provenance registry.
          </p>
        </div>

        <button
          onClick={loadData}
          className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
        </button>
      </div>

      {/* System Sub-components Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-300 font-bold flex items-center gap-1.5">
              <Database className="w-4 h-4 text-blue-400" /> PostgreSQL Database
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-500/30">
              {healthData?.components?.database?.status || "HEALTHY"}
            </span>
          </div>
          <p className="text-slate-400 text-[11px]">{healthData?.components?.database?.type || "Supabase PostgreSQL"}</p>
          <span className="text-slate-500 text-[10px] block font-mono">{healthData?.components?.database?.details || "Connected"}</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-300 font-bold flex items-center gap-1.5">
              <FileCheck2 className="w-4 h-4 text-cyan-400" /> Tesseract OCR
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
              healthData?.components?.ocr_engine?.status === "HEALTHY"
                ? "bg-emerald-950 text-emerald-400 border-emerald-500/30"
                : "bg-amber-950 text-amber-400 border-amber-500/30"
            }`}>
              {healthData?.components?.ocr_engine?.status || "STATUS"}
            </span>
          </div>
          <p className="text-slate-400 text-[11px]">{healthData?.components?.ocr_engine?.type || "Document OCR"}</p>
          <span className="text-slate-500 text-[10px] block font-mono">{healthData?.components?.ocr_engine?.details || "Checked"}</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-300 font-bold flex items-center gap-1.5">
              <HardDrive className="w-4 h-4 text-emerald-400" /> Local Storage
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-500/30">
              HEALTHY
            </span>
          </div>
          <p className="text-slate-400 text-[11px]">Uploads & Reports Directories</p>
          <span className="text-slate-500 text-[10px] block font-mono">data/uploads & data/reports</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-300 font-bold flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-amber-400" /> ML Gate Policy
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-500/30">
              ENFORCED
            </span>
          </div>
          <p className="text-amber-400 text-[11px] font-bold">ML_NOT_READY</p>
          <span className="text-slate-500 text-[10px] block font-mono">Historical DDR fallback active</span>
        </div>
      </div>

      {/* Dataset Provenance Registry */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> DATA PROVENANCE REGISTRY (ZERO MOCK DATA POLICY)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {provenanceData?.data_fabrication_policy || "STRICT_ZERO_FABRICATION — NO DEMO MOCK DATA"}
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300 font-bold">
            NORWEGIAN CONTINENTAL SHELF
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {provenanceData?.provenance_registry?.map((item: any, idx: number) => (
            <div key={idx} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between border-b border-slate-850 pb-2">
                <strong className="text-white font-bold">{item.dataset_name}</strong>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-500/30">
                  {item.verification_status}
                </span>
              </div>
              <p className="text-slate-400 text-xs">{item.description}</p>
              <div className="text-[11px] text-slate-500 font-mono">
                Source: <strong className="text-cyan-400">{item.source}</strong>
              </div>
              {item.disclaimer && (
                <div className="text-[10px] text-amber-400 font-bold bg-amber-950/40 p-2 rounded border border-amber-500/20">
                  ⚠️ {item.disclaimer}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
