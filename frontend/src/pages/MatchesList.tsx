import { useEffect, useRef } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, getMatches, getPipelineRuns } from "../lib/api";
import { runStatus } from "../lib/pipeline";
import { useProfile } from "../lib/profile-context";
import { useSearchFilters } from "../hooks/useSearchFilters";
import {
  DEFAULT_FILTERS,
  isDefaultFilters,
  matchesKeywords,
} from "../lib/searchFilters";
import FiltersSidebar from "../components/FiltersSidebar";
import MatchCard from "../components/MatchCard";
import MatchDetailDrawer from "../components/MatchDetailDrawer";
import SourceAttribution from "../components/SourceAttribution";
import Logo from "../components/ui/Logo";
import { BriefcaseIcon, RefreshIcon, XIcon } from "../components/ui/icons";

export default function MatchesList() {
  const { profileId, logout } = useProfile();
  const { filters, update } = useSearchFilters();
  const { jobId } = useParams<{ jobId?: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: runsData } = useQuery({
    queryKey: ["pipeline-runs-light"],
    queryFn: () => getPipelineRuns(4, false),
    refetchInterval: 30_000,
  });
  const pipelineRunning = (runsData?.runs ?? []).some((r) => runStatus(r) === "running");

  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !pipelineRunning) {
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      queryClient.invalidateQueries({ queryKey: ["technologies"] });
      toast.success("Pipeline finalizado — matches actualizados");
    }
    wasRunning.current = pipelineRunning;
  }, [pipelineRunning, queryClient]);

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["matches", profileId, filters],
    queryFn: () => getMatches(20, filters),
    enabled: profileId !== null,
    placeholderData: keepPreviousData,
    refetchInterval: pipelineRunning ? 15_000 : false,
  });

  const isProfileMissing = error instanceof ApiError && error.status === 404;

  const filtersActive = !isDefaultFilters(filters);
  const visibleMatches = (data?.matches ?? []).filter((m) =>
    matchesKeywords(m, filters.keywords),
  );

  return (
    <main className="max-w-[1280px] mx-auto px-6 pt-8 pb-24 animate-fade-in">
      {pipelineRunning && (
        <div className="flex items-center gap-3 px-4 py-3 mb-5 bg-accent-soft border border-accent-line rounded-[10px]">
          <span className="w-4 h-4 inline-flex text-accent animate-spin">
            <RefreshIcon size={16} />
          </span>
          <div className="flex-1">
            <div className="font-semibold text-fg">Pipeline en ejecución</div>
            <div className="text-sm text-sub">
              Los matches se actualizan automáticamente mientras corre.
            </div>
          </div>
        </div>
      )}

      <div className="flex items-end justify-between mb-[22px]">
        <div>
          <h1 className="m-0 text-2xl font-bold tracking-[-0.02em]">Matches</h1>
          <div className="mt-1.5 flex items-center gap-2.5 flex-wrap">
            <p className="m-0 text-sm text-sub">
              {data
                ? filtersActive
                  ? `${visibleMatches.length} ofertas · filtros aplicados`
                  : `${data.count} ofertas · ordenadas por relevancia`
                : " "}
            </p>
            {filtersActive && (
              <button
                type="button"
                onClick={() => update(DEFAULT_FILTERS)}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-accent-soft border border-accent-line rounded-md text-xs font-medium text-accent-text"
              >
                Filtros activos · limpiar
                <XIcon size={11} />
              </button>
            )}
            {isFetching && filtersActive && (
              <span className="text-xs text-muted">Aplicando filtros…</span>
            )}
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-3.5 text-[13px] text-muted">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-score-green" />
            ≥70
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-score-amber" />
            40–69
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-score-red" />
            &lt;40
          </span>
        </div>
      </div>

      <div className="flex gap-6 items-start">
        <FiltersSidebar filters={filters} onChange={update} />
        <div className="flex-1 min-w-0">
      {isLoading && <SkeletonList />}

      {isProfileMissing && (
        <div className="text-center px-6 py-[72px] bg-panel border border-line rounded-2xl">
          <div className="mx-auto mb-5 w-fit">
            <Logo size={56} radius={15} fontSize={22} />
          </div>
          <h2 className="m-0 mb-2.5 text-xl font-bold tracking-[-0.01em]">
            Creá tu perfil para empezar
          </h2>
          <p className="mx-auto mb-[26px] max-w-[460px] text-[15px] text-sub leading-relaxed">
            JobMatch rankea ofertas remotas contra tu perfil profesional. Contanos tu stack,
            seniority y un resumen — el matching semántico hace el resto.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              to="/profile"
              className="inline-flex items-center h-10 px-[22px] bg-accent rounded-[10px] text-accent-ink font-semibold text-[15px]"
            >
              Crear perfil
            </Link>
            <button
              type="button"
              onClick={logout}
              className="h-10 px-[18px] bg-transparent border border-line-2 rounded-[10px] text-fg font-medium text-sm"
            >
              Cambiar ID
            </button>
          </div>
        </div>
      )}

      {error && !isProfileMissing && (
        <div className="text-center px-6 py-[72px] bg-neg-soft border border-neg-line rounded-2xl">
          <div className="w-[52px] h-[52px] mx-auto mb-[18px] rounded-[14px] bg-neg-soft border border-neg-line flex items-center justify-center text-neg">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 className="m-0 mb-2 text-lg font-semibold">No se pudieron cargar los matches</h2>
          <p className="mx-auto mb-1.5 max-w-[440px] text-sm text-fg-2">
            La API respondió con un error. Revisá el estado del sistema y volvé a intentar.
          </p>
          <p className="mx-auto mb-6 font-mono text-[13px] text-neg">
            {error instanceof ApiError ? `${error.status} · error` : error.message}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="h-[38px] px-[18px] bg-transparent border border-line-2 rounded-[9px] text-fg font-medium text-sm"
          >
            Reintentar
          </button>
        </div>
      )}

      {data && data.count === 0 && !filtersActive && (
        <div className="text-center px-6 py-[72px] bg-panel border border-line rounded-2xl">
          <div className="w-[52px] h-[52px] mx-auto mb-[18px] rounded-[14px] bg-panel2 border border-line-2 flex items-center justify-center text-muted">
            <BriefcaseIcon size={24} />
          </div>
          <h2 className="m-0 mb-2 text-lg font-semibold">Todavía no hay matches</h2>
          <p className="mx-auto mb-6 max-w-[420px] text-sm text-sub">
            El pipeline todavía no scoreó ofertas para este perfil. Corré un refresh para
            recolectar y evaluar ofertas nuevas.
          </p>
          <Link
            to="/search"
            className="inline-flex items-center h-[38px] px-[18px] bg-accent rounded-[9px] text-accent-ink font-semibold text-sm"
          >
            Programar búsqueda
          </Link>
        </div>
      )}

      {data && (data.count > 0 || filtersActive) && (
        <>
          {visibleMatches.length === 0 ? (
            <div className="text-center px-6 py-12 bg-panel border border-line rounded-2xl">
              <p className="m-0 mb-4 text-sm text-sub">
                Ningún match pasa los filtros actuales.
              </p>
              <button
                type="button"
                onClick={() => update(DEFAULT_FILTERS)}
                className="h-9 px-4 bg-transparent border border-line-2 rounded-[9px] text-fg font-medium text-sm"
              >
                Limpiar filtros
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {visibleMatches.map((match) => (
                <MatchCard key={match.job_id} match={match} />
              ))}
            </div>
          )}
          <SourceAttribution text={data.source_attribution} />
        </>
      )}
        </div>
      </div>

      {jobId && <MatchDetailDrawer jobId={jobId} onClose={() => navigate("/")} />}
    </main>
  );
}

function SkeletonList() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex gap-5 px-5 py-[18px] bg-panel border border-line rounded-[14px]">
          <div className="flex-1">
            <div className="h-4 w-[42%] bg-panel2 rounded-md animate-pulse" />
            <div className="h-3 w-[24%] bg-hair rounded-md mt-3 animate-pulse" />
            <div className="h-3 w-[60%] bg-hair rounded-md mt-[18px] animate-pulse" />
          </div>
          <div className="w-[76px] h-16 bg-hair rounded-xl animate-pulse" />
        </div>
      ))}
    </div>
  );
}
