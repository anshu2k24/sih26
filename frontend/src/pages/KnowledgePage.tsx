import React from "react";
import { useNavigate } from "react-router-dom";
import { KnowledgeRepository } from "./KnowledgeRepository";
import type { HistoricalEventEpisode } from "../types/api";

export const KnowledgePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <KnowledgeRepository
        onOpenEventDetail={(ev: HistoricalEventEpisode) => navigate(`/events/${encodeURIComponent(ev.event_episode_id)}`)}
        onOpenWellIntelligence={(wellId: string) => navigate(`/wells/${encodeURIComponent(wellId)}`)}
      />
    </div>
  );
};
