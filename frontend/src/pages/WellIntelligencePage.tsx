import React from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useActiveWell } from "../context/ActiveWellContext";
import { OffsetWellIntelligence } from "./OffsetWellIntelligence";
import { ArrowLeft, Shield } from "lucide-react";

export const WellIntelligencePage: React.FC = () => {
  const { wellId } = useParams<{ wellId: string }>();
  const { selectedWell } = useActiveWell();
  const navigate = useNavigate();

  const targetWell = wellId ? decodeURIComponent(wellId) : selectedWell;

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb Header */}
      <div className="flex items-center justify-between font-mono text-xs border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Link
            to="/dashboard"
            className="text-slate-400 hover:text-white flex items-center gap-1 hover:underline"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-slate-400">Offset Wells</span>
          <span className="text-slate-600">/</span>
          <span className="text-blue-400 font-bold">{targetWell}</span>
        </div>

        <div className="flex items-center gap-2 text-slate-400">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>Equinor Volve Verified DDR Profile</span>
        </div>
      </div>

      {/* Embedded Offset Well Intelligence View */}
      <OffsetWellIntelligence
        wellIdParam={targetWell}
        activeWellId={selectedWell}
        onOpenEventDetail={(ev) => navigate(`/events/${encodeURIComponent(ev.event_episode_id)}`)}
      />
    </div>
  );
};
