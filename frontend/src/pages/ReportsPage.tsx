import React, { useState, useEffect } from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { generateReportApi, fetchReportsListApi } from "../services/api";
import {
  FileText,
  Download,
  PlusCircle,
  RefreshCw,
  Eye,
  XCircle,
  Sparkles,
} from "lucide-react";

export const ReportsPage: React.FC = () => {
  const { selectedWell, currentMd } = useActiveWell();
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);

  // Form selection
  const [reportType, setReportType] = useState<string>("DDR");
  const [outgoingEng, setOutgoingEng] = useState<string>("Drilling Superintendent");

  // Selected report modal view
  const [selectedReportModal, setSelectedReportModal] = useState<any | null>(null);

  const loadReports = async () => {
    setLoading(true);
    const data = await fetchReportsListApi(selectedWell);
    if (data && data.reports) {
      setReports(data.reports);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadReports();
  }, [selectedWell]);

  const handleGenerateReport = async () => {
    setGenerating(true);
    const res = await generateReportApi(reportType, selectedWell, currentMd, outgoingEng);
    setGenerating(false);
    if (res && res.report) {
      setSelectedReportModal(res.report);
      loadReports();
    }
  };

  const handleDownloadMarkdown = (reportItem: any) => {
    const content = reportItem.content_md || `# ${reportItem.title}\nReport ID: ${reportItem.id}\nWell: ${reportItem.well_id}`;
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${reportItem.id || reportItem.report_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getReportTypeBadge = (type: string) => {
    switch (type) {
      case "DDR":
        return "bg-blue-950 text-blue-400 border-blue-500/30";
      case "SHIFT_HANDOVER":
        return "bg-indigo-950 text-indigo-400 border-indigo-500/30";
      case "INCIDENT_SUMMARY":
        return "bg-rose-950 text-rose-400 border-rose-500/30";
      default:
        return "bg-slate-950 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-blue-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              OPERATIONAL REPORT & SHIFT HANDOVER CONSOLE
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-blue-950/80 text-blue-400 border border-blue-500/30 font-bold">
              EQUINOR VOLVE PROVENANCED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Generate Daily Drilling Reports (DDR), Shift Handover Summaries, and Incident Reports with telemetry metrics and audit history.
          </p>
        </div>

        <button
          onClick={loadReports}
          className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
        </button>
      </div>

      {/* Report Generator Panel */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <PlusCircle className="w-4 h-4 text-blue-400" /> Generate New Operational Report
          </h2>
          <span className="text-xs text-slate-400">Target Well: <strong className="text-white">{selectedWell}</strong> | MD: <strong className="text-emerald-400">{currentMd.toFixed(1)} m</strong></span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="text-slate-400 font-bold block mb-1.5">REPORT TYPE:</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 text-white rounded-lg p-2.5 font-bold focus:outline-none focus:border-blue-500"
            >
              <option value="DDR">DAILY DRILLING REPORT (DDR)</option>
              <option value="SHIFT_HANDOVER">SHIFT HANDOVER REPORT</option>
              <option value="INCIDENT_SUMMARY">INCIDENT & PROXIMITY SUMMARY</option>
            </select>
          </div>

          <div>
            <label className="text-slate-400 font-bold block mb-1.5">SUPERINTENDENT / SIGN-OFF:</label>
            <input
              type="text"
              value={outgoingEng}
              onChange={(e) => setOutgoingEng(e.target.value)}
              placeholder="Enter engineer name / title..."
              className="w-full bg-slate-950 border border-slate-700 text-white rounded-lg p-2.5 font-mono focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleGenerateReport}
              disabled={generating}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 text-xs uppercase tracking-wider"
            >
              <Sparkles className={`w-4 h-4 ${generating ? "animate-spin" : ""}`} />
              {generating ? "GENERATING..." : "GENERATE REPORT"}
            </button>
          </div>
        </div>
      </div>

      {/* Generated Reports Archive Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs font-bold text-slate-300">
          <span>Generated Reports Archive ({reports.length} records)</span>
          <span className="text-slate-500">Format: Markdown & Struct JSON</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 font-bold">
                <th className="p-3.5">REPORT ID</th>
                <th className="p-3.5">TYPE</th>
                <th className="p-3.5">WELL ID</th>
                <th className="p-3.5">TITLE</th>
                <th className="p-3.5">MD DEPTH</th>
                <th className="p-3.5">CREATED AT</th>
                <th className="p-3.5 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {reports.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500">
                    No reports generated yet for well {selectedWell}. Click 'GENERATE REPORT' above.
                  </td>
                </tr>
              )}
              {reports.map((rep) => (
                <tr key={rep.id || rep.report_id} className="hover:bg-slate-850/60 transition-all">
                  <td className="p-3.5 font-bold text-blue-400 font-mono">{rep.id || rep.report_id}</td>
                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getReportTypeBadge(rep.report_type)}`}>
                      {rep.report_type}
                    </span>
                  </td>
                  <td className="p-3.5 text-white font-bold">{rep.well_id}</td>
                  <td className="p-3.5 text-slate-200">{rep.title}</td>
                  <td className="p-3.5 text-emerald-400 font-bold">{rep.current_md ? `${rep.current_md.toFixed(1)} m` : "N/A"}</td>
                  <td className="p-3.5 text-slate-400">{new Date(rep.created_at || rep.generated_at).toLocaleString()}</td>
                  <td className="p-3.5 text-right flex items-center justify-end gap-2">
                    <button
                      onClick={() => setSelectedReportModal(rep)}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-2.5 py-1 rounded border border-slate-700 font-bold transition-all flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5 text-cyan-400" /> PREVIEW
                    </button>
                    <button
                      onClick={() => handleDownloadMarkdown(rep)}
                      className="bg-blue-950 hover:bg-blue-900 text-blue-300 border border-blue-500/30 text-xs px-2.5 py-1 rounded font-bold transition-all flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" /> EXPORT MD
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Report Preview Modal */}
      {selectedReportModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-3xl w-full p-6 space-y-4 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setSelectedReportModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <XCircle className="w-5 h-5" />
            </button>

            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border inline-block mb-1 ${getReportTypeBadge(selectedReportModal.report_type)}`}>
                  {selectedReportModal.report_type}
                </span>
                <h2 className="text-base font-bold text-white uppercase tracking-wider">
                  {selectedReportModal.title}
                </h2>
              </div>
              <button
                onClick={() => handleDownloadMarkdown(selectedReportModal)}
                className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 shadow-lg shadow-blue-500/20"
              >
                <Download className="w-4 h-4" /> DOWNLOAD MARKDOWN
              </button>
            </div>

            {/* Formatted Content View */}
            <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 text-xs text-slate-200 space-y-3 font-mono overflow-x-auto">
              <pre className="whitespace-pre-wrap leading-relaxed font-mono">
                {selectedReportModal.content_md || JSON.stringify(selectedReportModal, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setSelectedReportModal(null)}
                className="bg-slate-800 text-slate-300 px-4 py-1.5 rounded-lg font-bold text-xs"
              >
                CLOSE PREVIEW
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
