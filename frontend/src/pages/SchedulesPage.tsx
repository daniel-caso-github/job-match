import { useState } from "react";
import { Link } from "react-router-dom";
import { useNow } from "../hooks/useNow";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelSearch, getPipelineRuns, getSavedSearches } from "../lib/api";
import { toast } from "sonner";
import { formatDateTime, relativeTime } from "../lib/format";
import {
  buildProgItems,
  progItemMeta,
  runDuration,
  searchFiltersFrom,
  shortId,
  summaryChips,
  type ProgItem,
} from "../lib/pipeline";
import { useProfile } from "../lib/profile-context";
import { selectedSeniorities, type SearchFilters } from "../lib/searchFilters";
import StageStepper, { StageRows } from "../components/StageStepper";
import StatusChip, { STATUS_DOT } from "../components/StatusChip";
import Drawer from "../components/ui/Drawer";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import { EyeIcon, XIcon } from "../components/ui/icons";

const ATTRIBUTION =
  "Jobs via Himalayas (himalayas.app), Remotive (remotive.com), Jobicy (jobicy.com), Remote OK (remoteok.com), Arbeitnow (arbeitnow.com), Adzuna (adzuna.com) and Jooble (jooble.org). Original postings linked in each match.";

type ProgFilter = "all" | "active" | "done";

const FILTER_TABS: { value: ProgFilter; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "active", label: "Activas" },
  { value: "done", label: "Finalizadas" },
];

interface Row {
  label: string;
  value: string | null;
}

function DetailRow({ label, value, fallback = "No especificado" }: Row & { fallback?: string }) {
  return (
    <div className="flex justify-between gap-4 py-2 border-t border-hair text-[13px]">
      <span className="text-sub flex-none">{label}</span>
      <span
        className={`font-medium text-right ${value === null ? "italic text-muted" : "text-fg"}`}
      >
        {value ?? fallback}
      </span>
    </div>
  );
}

function criteriaRows(f: SearchFilters): Row[] {
  const sources = (["himalayas", "remotive", "jobicy", "remoteok", "arbeitnow", "adzuna", "jooble"] as const).filter((s) => f.sources[s]);
  const salaryRange =
    f.salaryMinUsd > 0 || f.salaryMaxUsd > 0
      ? `USD ${f.salaryMinUsd > 0 ? f.salaryMinUsd : "…"}–${f.salaryMaxUsd > 0 ? f.salaryMaxUsd : "…"}`
      : null;
  return [
    { label: "Fuentes", value: sources.length === 7 ? "Todas" : sources.join(", ") || null },
    { label: "Score LLM mínimo", value: f.minScore > 0 ? `≥ ${f.minScore}` : null },
    { label: "Seniority", value: selectedSeniorities(f).join(", ") || null },
    { label: "Inglés máximo", value: f.englishMax || null },
    { label: "Solo remoto", value: f.remoteOnly ? "Sí" : null },
    { label: "Solo LATAM-friendly", value: f.latamOnly ? "Sí" : null },
    { label: "Excluir residencia UE", value: f.excludeEU ? "Sí" : null },
    { label: "Solo con salario publicado", value: f.withSalary ? "Sí" : null },
    { label: "Rango salarial", value: salaryRange },
  ];
}

function buildTimeRows(item: ProgItem): Row[] {
  const { run, search } = item;
  return [
    {
      label: "Creada",
      value: search?.created_at
        ? `${formatDateTime(search.created_at)} · ${relativeTime(search.created_at)}`
        : "—",
    },
    {
      label: "Ejecución programada",
      value: formatDateTime(search?.run_at ?? run?.logical_date ?? null),
    },
    { label: "Inicio real", value: run?.start_date ? formatDateTime(run.start_date) : "—" },
    { label: "Fin", value: run?.end_date ? formatDateTime(run.end_date) : "—" },
    { label: "Duración", value: run?.end_date ? runDuration(run) : "—" },
    {
      label: "Resultados",
      value: search?.match_count != null ? `${search.match_count} trabajos` : "—",
    },
  ];
}

function ProgDetailDrawer({ item, onClose }: { item: ProgItem; onClose: () => void }) {
  const { run, search } = item;
  const dagRunId = run?.dag_run_id ?? search?.dag_run_id ?? "";
  const filters = search ? searchFiltersFrom(search.filters) : null;
  const timeRows = buildTimeRows(item);

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
            <span className="text-[13px] font-semibold text-fg">Programación</span>
            <span className="font-mono text-xs text-muted">{shortId(dagRunId)}</span>
          </div>

          <div className="px-4 sm:px-6 py-6 flex flex-col gap-5 animate-fade-in">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 px-5 py-4 bg-app border border-hair rounded-xl">
              <div>
                <div className="text-[11px] font-semibold tracking-[0.06em] uppercase text-muted mb-1.5">
                  Tiempos de la ejecución
                </div>
                {timeRows.map((row) => (
                  <DetailRow key={row.label} {...row} fallback="—" />
                ))}
              </div>
              <div>
                <div className="text-[11px] font-semibold tracking-[0.06em] uppercase text-muted mb-1.5">
                  Criterios de la búsqueda
                </div>
                {filters ? (
                  criteriaRows(filters).map((row) => <DetailRow key={row.label} {...row} />)
                ) : (
                  <p className="m-0 py-2 text-[13px] italic text-muted">
                    Programación automática del perfil — sin criterios personalizados.
                  </p>
                )}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold tracking-[0.06em] uppercase text-muted mb-2">
                Etapas del pipeline
              </div>
              <StageRows tasks={run?.tasks ?? []} />
            </div>
          </div>
        </>
      )}
    </Drawer>
  );
}

function ProgCard({ item }: { item: ProgItem }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  useNow();
  const qc = useQueryClient();
  const { run, search, status } = item;
  const filters = search ? searchFiltersFrom(search.filters) : null;
  const keywords = filters ? [...filters.stack, ...filters.keywords] : [];
  const kwShown = keywords.slice(0, 6);
  const kwMore = keywords.length - kwShown.length;
  const dagRunId = run?.dag_run_id ?? search?.dag_run_id ?? "";
  const canCancel = status === "queued" && search != null;

  const cancelMutation = useMutation({
    mutationFn: () => cancelSearch(dagRunId),
    onSuccess: () => {
      setConfirmOpen(false);
      toast.success("Programación cancelada");
      qc.invalidateQueries({ queryKey: ["saved-searches"] });
      qc.invalidateQueries({ queryKey: ["pipeline-runs-all"] });
    },
    onError: () => {
      setConfirmOpen(false);
      toast.error("No se pudo cancelar — Airflow no disponible");
    },
  });

  return (
    <>
      <div className="flex gap-4">
        <div className="flex-none flex flex-col items-center w-3.5">
          <div
            className="w-3.5 h-3.5 rounded-full bg-app mt-[22px]"
            style={{ border: `2px solid ${STATUS_DOT[status]}` }}
          />
          <div className="flex-1 w-0.5 bg-line mt-1.5" />
        </div>

        <div className="flex-1 min-w-0 bg-panel border border-line rounded-2xl overflow-hidden">
          <div className="flex items-center gap-2.5 px-5 pt-4 pb-3 flex-wrap">
            <StatusChip status={status} />
            <span className="px-2 py-[3px] bg-chip border border-line-2 rounded-[7px] text-[11px] font-medium whitespace-nowrap text-sub">
              {run?.run_type === "scheduled" ? "Programada" : "Manual"}
            </span>
            <span className="text-[13px] text-fg-2">{progItemMeta(item)}</span>
            {search?.match_count != null && (
              <span className="px-2 py-[3px] bg-accent-soft border border-accent-line rounded-[7px] text-[11px] font-medium whitespace-nowrap text-accent-text">
                {search.match_count} {search.match_count === 1 ? "trabajo" : "trabajos"}
              </span>
            )}
            <div className="flex-1" />
            <span className="font-mono text-[11px] text-muted whitespace-nowrap">
              {shortId(dagRunId)}
            </span>
            {canCancel && (
              <button
                type="button"
                onClick={() => setConfirmOpen(true)}
                className="h-[30px] px-2.5 flex-none flex items-center rounded-lg border border-line-2 text-sub bg-transparent hover:border-neg hover:text-neg text-[11px] font-medium transition-colors"
              >
                Cancelar
              </button>
            )}
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="w-[30px] h-[30px] flex-none flex items-center justify-center bg-transparent border border-line-2 rounded-lg text-sub hover:text-fg hover:border-line-3 transition-colors"
            >
              <EyeIcon size={15} />
            </button>
          </div>

          {filters && (
            <>
              {keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5 px-5 pb-1.5">
                  {kwShown.map((kw) => (
                    <span
                      key={kw}
                      className="px-2 py-[3px] bg-panel2 border border-line-2 rounded-[7px] font-mono text-[11px] whitespace-nowrap text-accent-text"
                    >
                      {kw}
                    </span>
                  ))}
                  {kwMore > 0 && (
                    <span className="px-2 py-[3px] border border-dashed border-line-3 rounded-[7px] font-mono text-[11px] text-muted">
                      +{kwMore}
                    </span>
                  )}
                </div>
              )}
              <div className="flex flex-wrap gap-1.5 px-5 pb-3.5">
                {summaryChips(filters).map((chip) => (
                  <span
                    key={chip}
                    className="px-2 py-[3px] bg-chip border border-line-2 rounded-[7px] text-[11px] whitespace-nowrap text-fg-2"
                  >
                    {chip}
                  </span>
                ))}
              </div>
            </>
          )}

          <div className="px-6 pt-1.5 pb-5">
            <StageStepper tasks={run?.tasks ?? []} />
          </div>
        </div>
      </div>

      {confirmOpen && (
        <ConfirmDialog
          title="¿Cancelar esta programación?"
          description="Se eliminará la ejecución en cola y no se ejecutará. Esta acción no se puede deshacer."
          confirmLabel="Sí, cancelar"
          destructive
          loading={cancelMutation.isPending}
          onConfirm={() => cancelMutation.mutate()}
          onClose={() => setConfirmOpen(false)}
        />
      )}

      {drawerOpen && (
        <ProgDetailDrawer item={item} onClose={() => setDrawerOpen(false)} />
      )}
    </>
  );
}

const PAGE_SIZE = 4;

export default function SchedulesPage() {
  const { profileId } = useProfile();
  const [filter, setFilter] = useState<ProgFilter>("all");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["pipeline-runs-all"],
    queryFn: () => getPipelineRuns(25),
    refetchInterval: 30_000,
  });
  const { data: searchesData } = useQuery({
    queryKey: ["saved-searches", profileId],
    queryFn: () => getSavedSearches(),
    enabled: profileId !== null,
    refetchInterval: 30_000,
  });

  const runs = data?.runs ?? [];
  const searches = searchesData?.searches ?? [];

  const items = buildProgItems(runs, searches, profileId);

  const visible = items.filter((item) => {
    if (filter === "active") return item.status === "queued" || item.status === "running";
    if (filter === "done") return item.status === "success" || item.status === "failed";
    return true;
  });

  const runningCount = items.filter((i) => i.status === "running").length;
  const queuedCount = items.filter((i) => i.status === "queued").length;
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageItems = visible.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <main className="max-w-[1000px] mx-auto px-6 pt-8 pb-24 animate-fade-in">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 mb-[22px] text-sub text-sm hover:text-fg transition-colors"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
        Matches
      </Link>
      <div className="flex items-end justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1 className="m-0 text-2xl font-bold tracking-[-0.02em]">Programaciones</h1>
          <p className="mt-1.5 mb-0 text-[13px] text-sub">
            Cada búsqueda que programás dispara una ejecución del pipeline en Airflow. Acá ves
            ambas cosas en una sola línea.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-accent-soft border border-accent-line rounded-lg text-xs whitespace-nowrap text-accent-text">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            {runningCount} corriendo
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-panel2 border border-line-2 rounded-lg text-xs whitespace-nowrap text-sub">
            <span className="w-1.5 h-1.5 rounded-full bg-muted" />
            {queuedCount} en cola
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 mb-[18px]">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => { setFilter(tab.value); setPage(1); }}
            className={`h-8 px-3.5 rounded-lg text-[13px] transition-colors ${
              filter === tab.value
                ? "bg-accent text-accent-ink font-semibold"
                : "bg-panel border border-line-2 text-sub font-medium"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="flex flex-col gap-3.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-40 bg-panel border border-line rounded-2xl animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && visible.length === 0 && (
        <div className="text-center px-6 py-12 bg-panel border border-line rounded-2xl">
          <p className="m-0 mb-4 text-[13px] text-sub">
            {items.length === 0
              ? "Todavía no hay programaciones ni ejecuciones del pipeline."
              : "No hay programaciones en este estado."}
          </p>
          {items.length === 0 && (
            <Link
              to="/search"
              className="inline-flex items-center h-9 px-4 bg-accent rounded-[9px] text-accent-ink font-semibold text-[13px]"
            >
              Programar búsqueda
            </Link>
          )}
        </div>
      )}

      {visible.length > 0 && (
        <div className="flex flex-col gap-3.5">
          {pageItems.map((item) => (
            <ProgCard key={item.key} item={item} />
          ))}
        </div>
      )}

      {pageCount > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="h-8 px-3.5 rounded-lg text-[13px] font-medium bg-panel border border-line-2 text-sub transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Anterior
          </button>
          <span className="text-[13px] text-sub px-1">
            Página {currentPage} de {pageCount}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={currentPage === pageCount}
            className="h-8 px-3.5 rounded-lg text-[13px] font-medium bg-panel border border-line-2 text-sub transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Siguiente
          </button>
        </div>
      )}

      <footer className="mt-8 pt-5 border-t border-head-line">
        <p className="m-0 text-xs text-muted leading-relaxed">{ATTRIBUTION}</p>
      </footer>
    </main>
  );
}
