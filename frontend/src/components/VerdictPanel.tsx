import type { Verdict } from "../types/api";
import { CheckIcon, WarningIcon } from "./ui/icons";

interface Props {
  verdict: Verdict | null;
}

export default function VerdictPanel({ verdict }: Props) {
  return (
    <div className="p-[22px] bg-panel border border-line rounded-2xl">
      <h3 className="m-0 mb-[18px] text-sm font-semibold tracking-[0.04em] uppercase text-sub">
        Veredicto
      </h3>

      {verdict === null ? (
        <div className="text-center px-3 py-6">
          <div className="text-sm text-sub">
            El veredicto todavía no fue generado para esta oferta.
          </div>
          <div className="text-[13px] text-muted mt-1.5">Corré un refresh para scorearla.</div>
        </div>
      ) : (
        <>
          <div className="mb-[18px]">
            <div className="flex items-center gap-2 mb-2.5">
              <span className="w-4 h-4 text-pos">
                <CheckIcon size={16} />
              </span>
              <span className="text-sm font-semibold text-pos">Fortalezas</span>
            </div>
            <div className="flex flex-col gap-2">
              {verdict.strengths.map((s, i) => (
                <div key={i} className="flex gap-[9px] text-sm text-fg-2 leading-normal">
                  <span className="text-pos flex-none mt-0.5">+</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>

          {verdict.risks.length > 0 ? (
            <div>
              <div className="flex items-center gap-2 mb-2.5">
                <span className="w-4 h-4 text-neg">
                  <WarningIcon size={16} />
                </span>
                <span className="text-sm font-semibold text-neg">Riesgos</span>
              </div>
              <div className="flex flex-col gap-2">
                {verdict.risks.map((r, i) => (
                  <div key={i} className="flex gap-[9px] text-sm text-fg-2 leading-normal">
                    <span className="text-neg flex-none mt-0.5">−</span>
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-[9px] px-3 py-2.5 bg-pos-soft border border-pos-line rounded-[9px] text-[13px] text-pos">
              Sin riesgos identificados — match limpio.
            </div>
          )}
        </>
      )}
    </div>
  );
}
