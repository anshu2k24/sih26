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
  FolderOpen
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
        return "bg-[rgba(255,138,0,0.1)] text-[#FF9D1A] border-[rgba(255,138,0,0.3)] shadow-[0_0_10px_rgba(255,138,0,0.1)]";
      case "SHIFT_HANDOVER":
        return "bg-[rgba(56,189,248,0.1)] text-[#38BDF8] border-[rgba(56,189,248,0.3)] shadow-[0_0_10px_rgba(56,189,248,0.15)]";
      case "INCIDENT_SUMMARY":
        return "bg-[rgba(225,29,72,0.15)] text-[#FB7185] border-[rgba(225,29,72,0.4)] shadow-[0_0_10px_rgba(225,29,72,0.2)]";
      default:
        return "bg-[rgba(255,255,255,0.05)] text-[#A1A1AA] border-[rgba(255,255,255,0.1)]";
    }
  };

  return (
    <div 
      className="min-h-screen pb-[48px] relative font-['Space_Grotesk',sans-serif]"
      style={{ 
        backgroundColor: "#050505", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-map.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed"
      }}
    >
      <div className="relative z-10 max-w-[1600px] mx-auto px-[32px] pt-[32px] space-y-[24px]">
        {/* Header Banner */}
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6 relative">
          <div className="relative z-10 flex flex-col gap-[12px]">
            <div className="flex items-center gap-4 flex-wrap">
              <h1 className="text-[32px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
                OPERATIONAL REPORT & SHIFT HANDOVER CONSOLE
              </h1>
              <span 
                className="text-[11px] px-[10px] py-[4px] rounded-[6px] font-[700] uppercase tracking-wider flex items-center gap-1.5 mt-1"
                style={{ background: "rgba(56,189,248,0.1)", color: "#38BDF8", border: "1px solid rgba(56,189,248,0.3)", boxShadow: "0 0 10px rgba(56,189,248,0.15)" }}
              >
                EQUINOR VOLVE PROVENANCED
              </span>
            </div>
          </div>

          <div className="relative z-10 flex items-center gap-[16px] shrink-0">
            <button
              onClick={loadReports}
              className="flex items-center gap-[8px] px-[20px] py-[12px] rounded-[12px] font-[700] text-[13px] uppercase tracking-wider transition-all duration-200"
              style={{ background: "rgba(255,255,255,0.03)", color: "#D4D4D8", border: "1px solid rgba(255,255,255,0.1)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,138,0,0.1)";
                e.currentTarget.style.borderColor = "rgba(255,138,0,0.4)";
                e.currentTarget.style.color = "#FF9D1A";
                e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.15)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                e.currentTarget.style.color = "#D4D4D8";
                e.currentTarget.style.boxShadow = "none";
                e.currentTarget.style.transform = "none";
              }}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> REFRESH
            </button>
          </div>
        </div>

        {/* Report Generator Panel */}
        <div 
          className="rounded-[20px] p-[32px] space-y-[24px] transition-all duration-300 relative group"
          style={{
            background: "rgba(10, 10, 10, 0.72)",
            backdropFilter: "blur(18px)",
            border: "1px solid rgba(255, 138, 0, 0.25)",
            boxShadow: "0 5px 20px rgba(0,0,0,0.4)"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "rgba(255,138,0,0.35)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.25)";
          }}
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[rgba(255,138,0,0.2)] pb-[16px] gap-4">
            <h2 className="text-[14px] font-[700] text-white uppercase tracking-wider flex items-center gap-3 drop-shadow-sm font-['Space_Grotesk',sans-serif]">
              <PlusCircle className="w-5 h-5 text-[#FF9D1A]" /> GENERATE NEW OPERATIONAL REPORT
            </h2>
            <div className="text-[12px] text-[#A1A1AA] font-mono uppercase tracking-wider flex items-center gap-2">
              Target Well: <strong className="text-[#FF9D1A] ml-1">{selectedWell}</strong>
              <span className="text-[rgba(255,255,255,0.2)] mx-2">|</span>
              MD: <strong className="text-[#34D399] ml-1">{currentMd.toFixed(1)} m</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-[24px]">
            <div>
              <label className="text-[11px] text-[#A1A1AA] font-[700] uppercase tracking-widest block mb-[12px]">REPORT TYPE:</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full rounded-[12px] px-[16px] py-[14px] text-[13px] font-[700] text-white tracking-wide transition-all focus:outline-none appearance-none cursor-pointer"
                style={{
                  background: "rgba(0,0,0,0.6)",
                  border: "1px solid rgba(255,138,0,0.3)",
                  boxShadow: "inset 0 0 15px rgba(255,138,0,0.05)"
                }}
              >
                <option value="DDR" className="bg-[#050607]">DAILY DRILLING REPORT (DDR)</option>
                <option value="SHIFT_HANDOVER" className="bg-[#050607]">SHIFT HANDOVER REPORT</option>
                <option value="INCIDENT_SUMMARY" className="bg-[#050607]">INCIDENT & PROXIMITY SUMMARY</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] text-[#A1A1AA] font-[700] uppercase tracking-widest block mb-[12px]">SUPERINTENDENT / SIGN-OFF:</label>
              <input
                type="text"
                value={outgoingEng}
                onChange={(e) => setOutgoingEng(e.target.value)}
                placeholder="Enter engineer name / title..."
                className="w-full rounded-[12px] px-[16px] py-[14px] text-[13px] font-mono text-white transition-all focus:outline-none placeholder:text-[#6B7280]"
                style={{
                  background: "rgba(0,0,0,0.6)",
                  border: "1px solid rgba(255,255,255,0.1)",
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,138,0,0.4)";
                  e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.15)";
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={handleGenerateReport}
                disabled={generating}
                className="w-full py-[14px] rounded-[12px] font-[700] text-[14px] uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden"
                style={{
                  background: "linear-gradient(90deg, rgba(255,138,0,0.8), rgba(255,106,0,0.8))",
                  border: "1px solid rgba(255,170,100,0.5)",
                  color: "#FFFFFF",
                  boxShadow: "0 0 25px rgba(255,138,0,0.4), inset 0 0 15px rgba(255,255,255,0.2)"
                }}
                onMouseEnter={(e) => {
                  if(!generating) {
                    e.currentTarget.style.boxShadow = "0 0 40px rgba(255,138,0,0.6), inset 0 0 20px rgba(255,255,255,0.3)";
                    e.currentTarget.style.transform = "translateY(-2px) scale(1.01)";
                  }
                }}
                onMouseLeave={(e) => {
                  if(!generating) {
                    e.currentTarget.style.boxShadow = "0 0 25px rgba(255,138,0,0.4), inset 0 0 15px rgba(255,255,255,0.2)";
                    e.currentTarget.style.transform = "none";
                  }
                }}
              >
                <div className="absolute inset-0 bg-white opacity-[0.05] hover:opacity-[0.1] transition-opacity pointer-events-none"></div>
                <Sparkles className={`w-5 h-5 drop-shadow-[0_0_5px_rgba(255,255,255,0.6)] ${generating ? "animate-spin" : ""}`} />
                <span className="drop-shadow-md">{generating ? "GENERATING..." : "GENERATE REPORT"}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Generated Reports Archive Table */}
        <div 
          className="rounded-[20px] overflow-hidden flex flex-col transition-all duration-300 group relative"
          style={{
            background: "rgba(10, 10, 10, 0.72)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 138, 0, 0.25)",
            boxShadow: "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
            e.currentTarget.style.boxShadow = "0 15px 50px rgba(0,0,0,0.5), 0 0 30px rgba(255,138,0,0.08), inset 0 0 30px rgba(255,138,0,0.08)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.25)";
            e.currentTarget.style.boxShadow = "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)";
          }}
        >
          <div className="p-[24px] border-b border-[rgba(255,138,0,0.15)] flex items-center justify-between">
            <h2 className="text-[14px] font-[700] text-white uppercase tracking-wider flex items-center gap-3 font-['Space_Grotesk',sans-serif]">
              <FolderOpen className="w-5 h-5 text-[#FF9D1A]" /> GENERATED REPORTS ARCHIVE <span className="text-[#FF9D1A] font-mono">({reports.length} RECORDS)</span>
            </h2>
            <span className="text-[11px] text-[#A1A1AA] uppercase font-mono tracking-widest">
              Format: <strong className="text-[#FF9D1A]">Markdown & Struct JSON</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[1000px]">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.05)] bg-[rgba(0,0,0,0.2)]">
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">REPORT ID</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">TYPE</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">WELL ID</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">TITLE</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">MD DEPTH</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">CREATED AT</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.03)] font-mono text-[12px]">
                {reports.length === 0 && !loading && (
                  <tr>
                    <td colSpan={7} className="p-[80px]">
                      <div className="flex flex-col items-center justify-center space-y-[20px]">
                        <div className="relative flex items-center justify-center">
                          <div className="absolute inset-0 bg-[#FF8A00] opacity-[0.05] blur-[40px] rounded-full"></div>
                          <div 
                            className="w-[80px] h-[80px] rounded-full flex items-center justify-center border relative z-10"
                            style={{ background: "rgba(255,138,0,0.05)", borderColor: "rgba(255,138,0,0.3)", boxShadow: "0 0 30px rgba(255,138,0,0.15), inset 0 0 20px rgba(255,138,0,0.05)" }}
                          >
                            <FileText className="w-[32px] h-[32px] text-[#FF9D1A] drop-shadow-[0_0_8px_rgba(255,157,26,0.6)]" strokeWidth={1.5} />
                          </div>
                        </div>
                        <div className="text-center space-y-[8px]">
                          <div className="text-[16px] font-[700] text-white font-sans tracking-wide">
                            No reports generated yet for well {selectedWell}.
                          </div>
                          <div className="text-[13px] text-[#A1A1AA] font-sans">
                            Click <strong className="text-[#FF9D1A]">'GENERATE REPORT'</strong> above.
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                {reports.map((rep) => (
                  <tr 
                    key={rep.id || rep.report_id} 
                    className="transition-all duration-200"
                    style={{ background: "transparent" }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(255,138,0,0.03)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "transparent";
                    }}
                  >
                    <td className="p-[16px] font-[700] text-[#FF9D1A] tracking-wider">{rep.id || rep.report_id}</td>
                    <td className="p-[16px]">
                      <span className={`px-[8px] py-[4px] rounded-[6px] text-[10px] font-[700] uppercase tracking-wider border ${getReportTypeBadge(rep.report_type)}`}>
                        {rep.report_type}
                      </span>
                    </td>
                    <td className="p-[16px] text-white font-[700]">{rep.well_id}</td>
                    <td className="p-[16px] text-[#D4D4D8] truncate max-w-[200px]">{rep.title}</td>
                    <td className="p-[16px] text-[#34D399] font-[700]">{rep.current_md ? `${rep.current_md.toFixed(1)} m` : "N/A"}</td>
                    <td className="p-[16px] text-[#A1A1AA]">{new Date(rep.created_at || rep.generated_at).toLocaleString()}</td>
                    <td className="p-[16px] text-right flex items-center justify-end gap-[12px]">
                      <button
                        onClick={() => setSelectedReportModal(rep)}
                        className="flex items-center gap-[6px] px-[12px] py-[6px] rounded-[8px] font-[700] text-[11px] uppercase tracking-wider transition-all duration-200"
                        style={{ background: "rgba(255,255,255,0.03)", color: "#D4D4D8", border: "1px solid rgba(255,255,255,0.1)" }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = "rgba(56,189,248,0.1)";
                          e.currentTarget.style.borderColor = "rgba(56,189,248,0.4)";
                          e.currentTarget.style.color = "#38BDF8";
                          e.currentTarget.style.boxShadow = "0 0 15px rgba(56,189,248,0.15)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                          e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                          e.currentTarget.style.color = "#D4D4D8";
                          e.currentTarget.style.boxShadow = "none";
                        }}
                      >
                        <Eye className="w-3.5 h-3.5" /> PREVIEW
                      </button>
                      <button
                        onClick={() => handleDownloadMarkdown(rep)}
                        className="flex items-center gap-[6px] px-[12px] py-[6px] rounded-[8px] font-[700] text-[11px] uppercase tracking-wider transition-all duration-200"
                        style={{ background: "rgba(255,138,0,0.1)", color: "#FF9D1A", border: "1px solid rgba(255,138,0,0.3)" }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = "rgba(255,138,0,0.2)";
                          e.currentTarget.style.borderColor = "rgba(255,138,0,0.5)";
                          e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.2)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "rgba(255,138,0,0.1)";
                          e.currentTarget.style.borderColor = "rgba(255,138,0,0.3)";
                          e.currentTarget.style.boxShadow = "none";
                        }}
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
          <div className="fixed inset-0 z-50 bg-[rgba(0,0,0,0.85)] backdrop-blur-sm flex items-center justify-center p-[24px]">
            <div 
              className="rounded-[20px] max-w-4xl w-full p-[32px] space-y-[24px] relative max-h-[90vh] overflow-y-auto custom-scrollbar"
              style={{
                background: "rgba(10, 10, 10, 0.85)",
                border: "1px solid rgba(255, 138, 0, 0.35)",
                boxShadow: "0 20px 60px rgba(0,0,0,0.8), inset 0 0 30px rgba(255,138,0,0.08)"
              }}
            >
              <button
                onClick={() => setSelectedReportModal(null)}
                className="absolute top-[24px] right-[24px] text-[#A1A1AA] hover:text-[#FF3250] transition-colors"
              >
                <XCircle className="w-6 h-6" />
              </button>

              <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[rgba(255,138,0,0.2)] pb-[20px] gap-[16px]">
                <div>
                  <span className={`px-[10px] py-[4px] rounded-[6px] text-[11px] font-[700] uppercase tracking-wider border inline-block mb-[12px] ${getReportTypeBadge(selectedReportModal.report_type)}`}>
                    {selectedReportModal.report_type}
                  </span>
                  <h2 className="text-[20px] font-[700] text-white uppercase tracking-wider font-['Space_Grotesk',sans-serif] drop-shadow-sm">
                    {selectedReportModal.title}
                  </h2>
                </div>
                <button
                  onClick={() => handleDownloadMarkdown(selectedReportModal)}
                  className="flex items-center gap-[8px] px-[20px] py-[12px] rounded-[12px] font-[700] text-[13px] uppercase tracking-wider transition-all duration-200"
                  style={{ background: "rgba(255,138,0,0.15)", color: "#FF9D1A", border: "1px solid rgba(255,138,0,0.4)" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(255,138,0,0.25)";
                    e.currentTarget.style.borderColor = "#FF9D1A";
                    e.currentTarget.style.boxShadow = "0 0 20px rgba(255,138,0,0.25)";
                    e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(255,138,0,0.15)";
                    e.currentTarget.style.borderColor = "rgba(255,138,0,0.4)";
                    e.currentTarget.style.boxShadow = "none";
                    e.currentTarget.style.transform = "none";
                  }}
                >
                  <Download className="w-4 h-4" /> EXPORT MD
                </button>
              </div>

              {/* Formatted Content View */}
              <div 
                className="p-[24px] rounded-[16px] text-[13px] text-[#D4D4D8] font-mono overflow-x-auto custom-scrollbar"
                style={{
                  background: "rgba(0,0,0,0.6)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  boxShadow: "inset 0 0 20px rgba(0,0,0,0.5)"
                }}
              >
                <pre className="whitespace-pre-wrap leading-relaxed">
                  {selectedReportModal.content_md || JSON.stringify(selectedReportModal, null, 2)}
                </pre>
              </div>

              <div className="flex justify-end pt-[16px] border-t border-[rgba(255,138,0,0.15)]">
                <button
                  onClick={() => setSelectedReportModal(null)}
                  className="px-[24px] py-[12px] rounded-[12px] text-[13px] font-[700] text-[#A1A1AA] uppercase tracking-wider transition-colors hover:text-white hover:bg-[rgba(255,255,255,0.05)] border border-transparent hover:border-[rgba(255,255,255,0.1)]"
                >
                  CLOSE PREVIEW
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
