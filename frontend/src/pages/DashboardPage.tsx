import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useActiveWell } from "../context/ActiveWellContext";
import { CurrentDrillingState } from "../components/telemetry/CurrentDrillingState";
import { HistoricalProximityPanel } from "../components/events/HistoricalProximityPanel";
import { NearbyWellsMap } from "../components/map/NearbyWellsMap";
import { TelemetryCards } from "../components/telemetry/TelemetryCards";
import { SystemStatus } from "../components/system/SystemStatus";
import { Map, ArrowRight, X, Sparkles, AlertTriangle, Shield } from "lucide-react";
import type { HistoricalEventEpisode } from "../types/api";

export const DashboardPage: React.FC = () => {
  const { wells, selectedWell, setSelectedWell, currentMd, tvd, status, samplesReceived, lastTimestamp, latestSensor, mlState } = useActiveWell();
  const navigate = useNavigate();
  const [selectedEventModal, setSelectedEventModal] = useState<HistoricalEventEpisode | null>(null);

  const getEventBadgeStyle = (eventType: string) => {
    switch (eventType) {
      case "FORMATION_MUD_LOSS":
      case "CEMENTING/OPERATIONAL_LOSS":
        return "bg-rose-950/80 text-rose-400 border-rose-500/40";
      case "Tight Hole":
      case "Pack-off":
        return "bg-amber-950/80 text-amber-400 border-amber-500/40";
      case "Stuck Pipe":
      case "Kick":
        return "bg-purple-950/80 text-purple-400 border-purple-500/40";
      case "Equipment Failure":
        return "bg-blue-950/80 text-blue-400 border-blue-500/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div 
      className="relative min-h-[calc(100vh-6rem)] -m-4 sm:-m-6 bg-cover bg-no-repeat bg-fixed"
      style={{ 
        backgroundImage: 'url("/src/assets/hero_sunset.png")',
        backgroundPosition: 'center bottom'
      }}
    >
      {/* Subtle overlay to ensure text remains readable without dulling the image */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#02050A]/70 via-transparent to-[#02050A]/30 z-0" />
      
      {/* MAIN CONTENT WRAPPER FOR SIDEBAR CLEARANCE */}
      <div className="relative z-10 w-full px-6 sm:px-8">

        {/* 1. HERO / COMMAND CENTER INTRODUCTION */}
        <div className="w-full pt-12 pb-28 space-y-6">
          
          <div className="flex items-center gap-2 text-amber-500 font-bold tracking-widest text-xs uppercase font-mono">
            <Sparkles className="w-4 h-4" />
            Drilling Telemetry & Geological Risk Mitigation
          </div>
          
          <h1 
            className="text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-[0.9] uppercase tracking-normal"
            style={{ fontFamily: "'Bebas Neue', sans-serif" }}
          >
            Real-Time Drilling <br/>
            Intelligence & Telemetry <br/>
            <span className="text-amber-500">Command Center</span>
          </h1>

        </div>

        {/* EXISTING DASHBOARD CONTENT (Shifted Below Hero) */}
        <div className="w-full pb-12 space-y-8 -mt-12">
        
        {/* 2. Key Operational Summary */}
        <div className="transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(255,140,0,0.12)] rounded-2xl">
          <CurrentDrillingState
            wellId={selectedWell}
            currentMd={currentMd}
            tvd={tvd}
            lastTimestamp={lastTimestamp}
            samplesReceived={samplesReceived}
          />
        </div>

        {/* 3. Historical Offset / Risk Information */}
        <div className="transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(255,140,0,0.12)] rounded-2xl">
          <HistoricalProximityPanel
            activeWellId={selectedWell}
            currentMd={currentMd}
            onOpenWellIntelligence={(wellId) => navigate(`/wells/${encodeURIComponent(wellId)}`)}
            onOpenEventDetail={(ev) => setSelectedEventModal(ev)}
          />
        </div>

        {/* 4. Real-time Telemetry Grid */}
        <div className="w-full transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(255,140,0,0.12)] rounded-2xl">
          <TelemetryCards latestSensor={latestSensor} />
        </div>

        {/* 5. System Status */}
        <div className="transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(255,140,0,0.12)] rounded-2xl">
          <SystemStatus streamStatus={status} mlState={mlState} />
        </div>
        </div>
      </div>

      {/* Event Detail Modal */}
      {selectedEventModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          style={{
            background: 'rgba(0,0,0,0.70)',
            backdropFilter: 'blur(6px)',
          }}
        >
          <div 
            className="relative w-full flex flex-col font-mono"
            style={{
              width: '90vw',
              maxWidth: '1250px',
              maxHeight: '90vh',
              background: 'rgba(10,10,10,0.88)',
              backdropFilter: 'blur(18px)',
              border: '1px solid rgba(255,122,0,0.45)',
              borderRadius: '20px',
              boxShadow: '0 0 40px rgba(255,122,0,0.12)',
              overflow: 'hidden'
            }}
          >
            {/* Header */}
            <header 
              className="sticky top-0 z-10 flex items-center justify-between px-6 py-5 shrink-0"
              style={{
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(10,10,10,0.95)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <div className="flex items-center gap-4">
                <div 
                  className="flex items-center justify-center w-10 h-10 shrink-0"
                  style={{
                    background: 'rgba(255,122,0,0.1)',
                    border: '1px solid rgba(255,122,0,0.3)',
                    borderRadius: '10px'
                  }}
                >
                  <AlertTriangle className="w-5 h-5" style={{ color: '#FF7A00' }} />
                </div>
                <span 
                  className="px-3 py-1 text-sm font-bold tracking-wider uppercase rounded"
                  style={{
                    color: '#FF7A00',
                    border: '1px solid rgba(255,122,0,0.4)',
                    background: 'rgba(255,122,0,0.05)'
                  }}
                >
                  {selectedEventModal.event_type}
                </span>
                <span className="text-sm tracking-wide" style={{ color: '#8A8A8A' }}>
                  Well: {selectedEventModal.well_id}
                </span>
              </div>
              <button
                onClick={() => setSelectedEventModal(null)}
                className="flex items-center justify-center transition-all duration-200 group w-10 h-10 shrink-0"
                style={{
                  background: 'rgba(20,20,20,0.8)',
                  border: '1px solid rgba(255,122,0,0.4)',
                  borderRadius: '50%'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#FF8A00';
                  e.currentTarget.style.boxShadow = '0 0 18px rgba(255,122,0,0.35)';
                  e.currentTarget.style.transform = 'scale(1.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255,122,0,0.4)';
                  e.currentTarget.style.boxShadow = 'none';
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                <X className="w-5 h-5" style={{ color: '#FF7A00' }} />
              </button>
            </header>

            {/* Scrollable Content */}
            <div 
              className="flex-1 overflow-y-auto px-6 py-6"
              style={{
                scrollbarWidth: 'thin',
                scrollbarColor: 'rgba(255,122,0,0.40) #080808'
              }}
            >
              <style>{`
                ::-webkit-scrollbar { width: 6px; }
                ::-webkit-scrollbar-track { background: #080808; }
                ::-webkit-scrollbar-thumb { background: rgba(255,122,0,0.40); border-radius: 3px; }
                ::-webkit-scrollbar-thumb:hover { background: rgba(255,122,0,0.70); }
              `}</style>
              
              {/* Summary Information Panel */}
              <div 
                className="grid grid-cols-3 gap-6"
                style={{
                  background: 'rgba(5,5,5,0.65)',
                  border: '1px solid rgba(255,122,0,0.30)',
                  borderRadius: '14px',
                  padding: '22px',
                  marginBottom: '18px'
                }}
              >
                <div>
                  <span className="block text-xs uppercase mb-1.5" style={{ color: '#8A8A8A' }}>Onset MD</span>
                  <span className="text-base font-bold" style={{ color: '#FF7A00' }}>{selectedEventModal.onset_md} m</span>
                </div>
                <div>
                  <span className="block text-xs uppercase mb-1.5" style={{ color: '#8A8A8A' }}>TVD</span>
                  <span className="text-base font-bold" style={{ color: '#FF7A00' }}>{selectedEventModal.onset_tvd ? `${selectedEventModal.onset_tvd} m` : "N/A"}</span>
                </div>
                <div>
                  <span className="block text-xs uppercase mb-1.5" style={{ color: '#8A8A8A' }}>Timestamp</span>
                  <span className="text-base font-bold" style={{ color: '#FF7A00' }}>{selectedEventModal.onset_timestamp || "N/A"}</span>
                </div>
              </div>

              {/* Observed Evidence */}
              <div 
                style={{
                  background: 'rgba(8,8,8,0.70)',
                  border: '1px solid rgba(0,208,132,0.20)',
                  borderRadius: '14px',
                  padding: '22px',
                  marginBottom: '16px'
                }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1 rounded bg-[#00D084]/10">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00D084" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                  </div>
                  <span className="text-sm font-bold uppercase tracking-wide" style={{ color: '#00D084' }}>Observed Evidence:</span>
                </div>
                <p className="text-[14px] leading-relaxed font-sans" style={{ color: '#F2F2F2' }}>
                  {selectedEventModal.primary_evidence || "None recorded"}
                </p>
              </div>

              {/* Mitigation Response */}
              <div 
                style={{
                  background: 'rgba(8,8,8,0.70)',
                  border: '1px solid rgba(59,130,246,0.20)',
                  borderRadius: '14px',
                  padding: '22px',
                  marginBottom: '16px'
                }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1 rounded bg-blue-500/10">
                    <Shield className="w-4 h-4 text-blue-400" />
                  </div>
                  <span className="text-sm font-bold uppercase tracking-wide text-blue-400">Mitigation Response:</span>
                </div>
                <p className="text-[14px] leading-relaxed font-sans" style={{ color: '#F2F2F2' }}>
                  {selectedEventModal.mitigation_text || "None recorded"}
                </p>
              </div>

              {/* Resolution Outcome */}
              <div 
                style={{
                  background: 'rgba(8,8,8,0.70)',
                  border: '1px solid rgba(255,170,0,0.20)',
                  borderRadius: '14px',
                  padding: '22px',
                  marginBottom: '22px'
                }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1 rounded bg-amber-500/10">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFAA00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                  </div>
                  <span className="text-sm font-bold uppercase tracking-wide" style={{ color: '#FFAA00' }}>Resolution Outcome:</span>
                </div>
                <p className="text-[14px] leading-relaxed font-sans" style={{ color: '#F2F2F2' }}>
                  {selectedEventModal.resolution_text || "None recorded"}
                </p>
              </div>
            </div>

            {/* Footer */}
            <footer 
              className="shrink-0 px-6 py-5 flex items-center justify-between"
              style={{
                borderTop: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(10,10,10,0.95)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <div className="text-sm">
                <span style={{ color: '#FF7A00' }}>Source: </span>
                <span style={{ color: '#F2F2F2' }}>
                  {selectedEventModal.source_label || `Equinor Volve DDR (${selectedEventModal.primary_source_record || 'Unknown'})`}
                </span>
              </div>
              <button
                onClick={() => {
                  const evId = selectedEventModal.event_episode_id;
                  setSelectedEventModal(null);
                  navigate(`/events/${encodeURIComponent(evId)}`);
                }}
                className="flex items-center gap-2 text-sm font-bold transition-all duration-200"
                style={{
                  background: 'rgba(255,122,0,0.12)',
                  border: '1px solid #FF7A00',
                  color: '#FFFFFF',
                  borderRadius: '10px',
                  padding: '12px 20px',
                  boxShadow: '0 0 10px rgba(255,122,0,0.1)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255,122,0,0.25)';
                  e.currentTarget.style.border = '1px solid #FF8A00';
                  e.currentTarget.style.boxShadow = '0 0 20px rgba(255,122,0,0.35)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255,122,0,0.12)';
                  e.currentTarget.style.border = '1px solid #FF7A00';
                  e.currentTarget.style.boxShadow = '0 0 10px rgba(255,122,0,0.1)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
                onMouseDown={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                OPEN FULL EVIDENCE PAGE ➔
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
};
