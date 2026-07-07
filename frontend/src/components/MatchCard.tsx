import { useNavigate } from "react-router-dom";
import type { MatchListItem } from "../types/api";
import { formatSemantic, safeHref } from "../lib/format";
import ScoreBadge from "./ScoreBadge";
import SourceBadge from "./SourceBadge";
import { CheckIcon, ExternalLinkIcon } from "./ui/icons";

interface Props {
  match: MatchListItem;
}

export default function MatchCard({ match }: Props) {
  const navigate = useNavigate();
  const pending = match.llm_score === null;
  const hasSem = match.semantic_score !== null;
  const topStrength =
    match.verdict?.strengths[0] ??
    (pending ? "Sin veredicto — scoring pendiente" : "Sin fortalezas destacadas");

  return (
    <div
      onClick={() => navigate(`/matches/${match.job_id}`)}
      className="flex gap-5 px-5 py-[18px] bg-panel border border-line rounded-[14px] cursor-pointer transition-colors hover:border-line-3"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2.5 flex-wrap mb-1.5">
          <span className="text-[17px] font-semibold text-fg tracking-[-0.01em]">
            {match.title}
          </span>
          <SourceBadge source={match.source} />
        </div>
        <div className="text-sm text-sub mb-3">
          {match.company}
          {match.country && <span className="ml-1.5 text-muted">· {match.country}</span>}
        </div>
        <div className="flex items-start gap-[9px] text-sm">
          <span className={`shrink-0 mt-px ${pending ? "text-muted" : "text-pos"}`}>
            <CheckIcon />
          </span>
          <span className="text-fg-2">{topStrength}</span>
        </div>
        <div className="flex items-center gap-4 mt-3.5">
          <a
            href={safeHref(match.url)}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-[5px] text-[13px] text-muted hover:text-accent-text transition-colors"
          >
            Ver oferta original
            <ExternalLinkIcon size={12} />
          </a>
        </div>
      </div>

      <div className="flex flex-col items-end justify-between gap-3 flex-none">
        <ScoreBadge score={match.llm_score} />
        <div className="w-28">
          <div className="flex justify-between gap-1.5 text-[11px] text-muted mb-1">
            <span className="tracking-[0.04em]">SEMÁNTICO</span>
            <span className={`font-mono ${hasSem ? "text-accent-text" : "text-muted"}`}>
              {formatSemantic(match.semantic_score)}
            </span>
          </div>
          <div className="h-1 rounded-[3px] bg-hair overflow-hidden">
            <div
              className="h-full rounded-[3px] bg-accent"
              style={{ width: hasSem ? `${Math.round(match.semantic_score! * 100)}%` : "0%" }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
