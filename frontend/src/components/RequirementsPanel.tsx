import type { JobRequirements } from "../types/api";
import { CheckIcon, WarningIcon } from "./ui/icons";

interface Props {
  requirements: JobRequirements | null;
  country?: string | null;
}

interface ReqRow {
  label: string;
  value: string | null;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default function RequirementsPanel({ requirements: r, country }: Props) {
  const rows: ReqRow[] = r
    ? [
        { label: "País", value: country ?? null },
        { label: "Seniority", value: r.seniority ? capitalize(r.seniority) : null },
        { label: "Inglés requerido", value: r.english_level },
        { label: "Remoto", value: r.remote === true ? "Sí" : r.remote === false ? "No" : null },
        { label: "Rango salarial", value: r.salary_range },
      ]
    : [];

  return (
    <div className="p-[22px] bg-panel border border-line rounded-2xl">
      <div className="flex items-center justify-between mb-[18px]">
        <h3 className="m-0 text-sm font-semibold tracking-[0.04em] uppercase text-sub">
          Requisitos
        </h3>
        {r && (
          <span
            title="Confianza de extracción del LLM"
            className="text-xs text-muted font-mono"
          >
            conf {r.confidence != null ? r.confidence.toFixed(2) : "—"}
          </span>
        )}
      </div>

      {r === null ? (
        <div className="text-center px-3 py-6">
          <div className="text-sm text-sub">Extracción de requisitos pendiente.</div>
          <div className="text-[13px] text-muted mt-1.5">El LLM todavía no procesó esta oferta.</div>
        </div>
      ) : (
        <>
          {(r.requires_eu_residency || r.latam_friendly !== null) && (
            <div className="flex flex-wrap gap-2 mb-[18px]">
              {r.requires_eu_residency && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-neg-soft border border-neg-line rounded-[7px] text-[13px] font-medium text-neg">
                  <WarningIcon size={13} />
                  Exige residencia en la UE
                </span>
              )}
              {r.latam_friendly === true && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-pos-soft border border-pos-line rounded-[7px] text-[13px] font-medium text-pos">
                  <CheckIcon size={13} />
                  LATAM-friendly
                </span>
              )}
              {r.latam_friendly === false && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-warn-soft border border-warn-line rounded-[7px] text-[13px] font-medium text-warn">
                  No LATAM-friendly
                </span>
              )}
            </div>
          )}

          <div className="mb-[18px]">
            <div className="text-xs text-muted mb-2 tracking-[0.04em]">STACK</div>
            <div className="flex flex-wrap gap-[7px]">
              {r.stack.map((tech) => (
                <span
                  key={tech}
                  className="px-2.5 py-1 bg-panel2 border border-line-2 rounded-[7px] font-mono text-[13px] text-accent-text"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>

          <div className="flex flex-col">
            {rows.map((row) => (
              <div
                key={row.label}
                className="flex items-center justify-between py-2.5 border-t border-hair"
              >
                <span className="text-sm text-sub">{row.label}</span>
                <span
                  className={`text-sm font-medium ${
                    row.value === null ? "italic text-muted" : "text-fg"
                  }`}
                >
                  {row.value ?? "No especificado"}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
