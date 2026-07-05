import { useQuery } from "@tanstack/react-query";
import { ApiError, getMatchDetail } from "../lib/api";
import { useProfile } from "../lib/profile-context";
import { formatSemantic, relativeTime, safeHref } from "../lib/format";
import Drawer from "./ui/Drawer";
import ScoreBadge from "./ScoreBadge";
import SourceBadge from "./SourceBadge";
import VerdictPanel from "./VerdictPanel";
import RequirementsPanel from "./RequirementsPanel";
import RawTextCollapsible from "./RawTextCollapsible";
import SourceAttribution from "./SourceAttribution";
import { ExternalLinkIcon, XIcon } from "./ui/icons";

interface Props {
  jobId: string;
  onClose: () => void;
}

export default function MatchDetailDrawer({ jobId, onClose }: Props) {
  const { profileId } = useProfile();

  const { data, isLoading, error } = useQuery({
    queryKey: ["match", jobId, profileId],
    queryFn: () => getMatchDetail(jobId),
    enabled: !!profileId,
  });

  const notFound = error instanceof ApiError && error.status === 404;

  return (
    <Drawer onClose={onClose}>
      {(requestClose) => (
        <>
      <div className="sticky top-0 z-10 flex items-center gap-2.5 h-[52px] px-4 sm:px-6 bg-head backdrop-blur-md border-b border-head-line">
        <button
          type="button"
          onClick={requestClose}
          title="Cerrar"
          className="w-8 h-8 -ml-1 flex items-center justify-center rounded-lg text-sub hover:text-fg hover:bg-panel2 transition-colors"
        >
          <XIcon size={15} />
        </button>
        {data && (
          <>
            <SourceBadge source={data.source} />
            <span className="font-mono text-xs text-muted">{data.job_id}</span>
            <span className="text-[13px] text-muted hidden sm:inline">
              · scoreado {relativeTime(data.scored_at)}
            </span>
          </>
        )}
      </div>

      <div className="px-4 sm:px-6 py-6 animate-fade-in">
        {isLoading && <SkeletonDrawer />}

        {notFound && (
          <div className="text-center px-6 py-[72px] bg-panel border border-line rounded-2xl">
            <h2 className="m-0 mb-2 text-lg font-semibold">Match no encontrado</h2>
            <p className="mx-auto mb-6 max-w-[420px] text-sm text-sub">
              Esta oferta no existe para el perfil{" "}
              <span className="font-mono text-accent-text">{profileId}</span>, o fue removida del
              pipeline.
            </p>
            <p className="m-0 mb-6 font-mono text-[13px] text-muted">404 · not_found</p>
            <button
              type="button"
              onClick={requestClose}
              className="h-[38px] px-[18px] bg-transparent border border-line-2 rounded-[9px] text-fg font-medium text-sm"
            >
              Cerrar
            </button>
          </div>
        )}

        {error && !notFound && (
          <div className="text-center px-6 py-[72px] bg-neg-soft border border-neg-line rounded-2xl">
            <h2 className="m-0 mb-2 text-lg font-semibold">No se pudo cargar el match</h2>
            <p className="mx-auto m-0 font-mono text-[13px] text-neg">
              {error instanceof ApiError ? `${error.status} · error` : error.message}
            </p>
          </div>
        )}

        {data && (
          <>
            <div className="p-5 sm:p-[26px] bg-panel border border-line rounded-2xl mb-4">
              <h1 className="m-0 mb-1.5 text-[22px] font-bold tracking-[-0.02em] leading-tight">
                {data.title}
              </h1>
              <div className="text-[15px] text-fg-2">{data.company}</div>

              <div className="flex gap-3 mt-5">
                <ScoreBadge score={data.llm_score} variant="hero" />
                <div className="flex flex-col items-center justify-center w-[104px] h-[104px] rounded-2xl bg-panel2 border border-line-2">
                  <span
                    className={`font-mono font-bold leading-none text-[32px] ${
                      data.semantic_score !== null ? "text-accent-text" : "text-muted"
                    }`}
                  >
                    {data.semantic_score !== null ? formatSemantic(data.semantic_score) : "—"}
                  </span>
                  <span className="text-[11px] tracking-[0.1em] uppercase text-sub mt-2">
                    Semántico
                  </span>
                </div>
              </div>

              <a
                href={safeHref(data.url)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-[7px] mt-5 h-[38px] px-4 bg-accent rounded-[9px] text-accent-ink font-semibold text-sm"
              >
                Ver oferta original
                <ExternalLinkIcon size={14} />
              </a>
            </div>

            <div className="flex flex-col gap-4">
              <VerdictPanel verdict={data.verdict} />
              <RequirementsPanel requirements={data.requirements} />
              {data.raw_text && <RawTextCollapsible text={data.raw_text} />}
            </div>

            <SourceAttribution text={data.source_attribution} />
          </>
        )}
      </div>
        </>
      )}
    </Drawer>
  );
}

function SkeletonDrawer() {
  return (
    <div className="flex flex-col gap-4">
      <div className="p-[26px] bg-panel border border-line rounded-2xl">
        <div className="h-5 w-[65%] bg-panel2 rounded-md animate-pulse" />
        <div className="h-4 w-[30%] bg-hair rounded-md mt-3 animate-pulse" />
        <div className="flex gap-3 mt-5">
          <div className="w-[104px] h-[104px] bg-hair rounded-2xl animate-pulse" />
          <div className="w-[104px] h-[104px] bg-hair rounded-2xl animate-pulse" />
        </div>
      </div>
      <div className="h-44 bg-panel border border-line rounded-2xl animate-pulse" />
      <div className="h-44 bg-panel border border-line rounded-2xl animate-pulse" />
    </div>
  );
}
