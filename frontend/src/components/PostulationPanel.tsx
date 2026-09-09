import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ApiError,
  approvePostulation,
  generatePostulation,
  getPostulation,
  rejectPostulation,
} from "../lib/api";
import type { PostulationPackage, PostulationStatus } from "../types/api";

interface Props {
  jobId: string;
}

const STATUS_LABEL: Record<PostulationStatus, string> = {
  pendiente_aprobacion: "Pendiente de aprobación",
  aprobado: "Aprobado",
  rechazado: "Rechazado",
};

const STATUS_CLS: Record<PostulationStatus, string> = {
  pendiente_aprobacion: "bg-accent-soft text-accent-text border border-accent-line",
  aprobado: "bg-pos-soft text-pos border border-pos-line",
  rechazado: "bg-neg-soft text-neg border border-neg-line",
};

async function copyToClipboard(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copiado`);
  } catch {
    toast.error("No se pudo copiar — copiá el texto manualmente.");
  }
}

export default function PostulationPanel({ jobId }: Props) {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["postulation", jobId],
    queryFn: () => getPostulation(jobId),
    retry: false,
  });

  const notGenerated = error instanceof ApiError && error.status === 404;

  const setPackage = (pkg: PostulationPackage) => {
    queryClient.setQueryData(["postulation", jobId], pkg);
  };

  const generateMutation = useMutation({
    mutationFn: () => generatePostulation(jobId),
    onSuccess: (pkg) => {
      setPackage(pkg);
      toast.success("Propuesta generada — revisala antes de aprobar.");
    },
    onError: () => toast.error("No se pudo generar la propuesta."),
  });

  const decideMutation = useMutation({
    mutationFn: (action: "approve" | "reject") =>
      action === "approve" ? approvePostulation(jobId) : rejectPostulation(jobId),
    onSuccess: (pkg) => {
      setPackage(pkg);
      toast.success(pkg.status === "aprobado" ? "Postulación aprobada" : "Postulación rechazada");
    },
  });

  return (
    <div className="p-[22px] bg-panel border border-line rounded-2xl">
      <div className="flex items-center justify-between mb-[18px]">
        <h3 className="m-0 text-sm font-semibold tracking-[0.04em] uppercase text-sub">
          Postulación
        </h3>
        {data && (
          <span
            className={`text-[11px] font-semibold px-2 py-1 rounded-md uppercase tracking-[0.04em] ${STATUS_CLS[data.status]}`}
          >
            {STATUS_LABEL[data.status]}
          </span>
        )}
      </div>

      {isLoading && <div className="text-sm text-sub">Cargando…</div>}

      {notGenerated && !data && (
        <div className="text-center px-3 py-6">
          <p className="m-0 mb-4 text-sm text-sub">
            Generá un CV ajustado y una carta de presentación a medida para esta oferta.
          </p>
          <button
            type="button"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="h-9 px-4 bg-accent rounded-[9px] text-accent-ink font-semibold text-sm disabled:opacity-60"
          >
            {generateMutation.isPending ? "Generando…" : "Generar propuesta"}
          </button>
        </div>
      )}

      {data && (
        <div className="flex flex-col gap-5">
          {data.skill_gap.met_requirements.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-fg-2 mb-2">Fortalezas detectadas</div>
              <ul className="m-0 pl-5 text-sm text-fg-2 flex flex-col gap-1">
                {data.skill_gap.met_requirements.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </div>
          )}

          {data.skill_gap.gaps.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-fg-2 mb-2">Brechas a justificar</div>
              <ul className="m-0 pl-5 text-sm text-fg-2 flex flex-col gap-1">
                {data.skill_gap.gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
              {data.skill_gap.notes && (
                <p className="mt-2 text-[13px] text-sub">{data.skill_gap.notes}</p>
              )}
            </div>
          )}

          {data.resume_bullets.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-fg-2">Bullets de CV sugeridos</div>
                <button
                  type="button"
                  onClick={() => copyToClipboard(data.resume_bullets.join("\n"), "Bullets")}
                  className="text-[13px] text-accent-text"
                >
                  Copiar
                </button>
              </div>
              <ul className="m-0 pl-5 text-sm text-fg-2 flex flex-col gap-1">
                {data.resume_bullets.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </div>
          )}

          {data.cover_letter && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-fg-2">Carta de presentación</div>
                <button
                  type="button"
                  onClick={() => copyToClipboard(data.cover_letter, "Carta")}
                  className="text-[13px] text-accent-text"
                >
                  Copiar
                </button>
              </div>
              <p className="m-0 whitespace-pre-wrap text-sm text-fg-2 leading-relaxed">
                {data.cover_letter}
              </p>
            </div>
          )}

          {data.status === "pendiente_aprobacion" ? (
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => decideMutation.mutate("approve")}
                disabled={decideMutation.isPending}
                className="h-9 px-4 bg-accent rounded-[9px] text-accent-ink font-semibold text-sm disabled:opacity-60"
              >
                Aprobar
              </button>
              <button
                type="button"
                onClick={() => decideMutation.mutate("reject")}
                disabled={decideMutation.isPending}
                className="h-9 px-4 bg-transparent border border-line-2 rounded-[9px] text-fg font-medium text-sm disabled:opacity-60"
              >
                Rechazar
              </button>
            </div>
          ) : (
            <div>
              <button
                type="button"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="h-9 px-4 bg-transparent border border-line-2 rounded-[9px] text-fg font-medium text-sm disabled:opacity-60"
              >
                {generateMutation.isPending ? "Generando…" : "Generar de nuevo"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
