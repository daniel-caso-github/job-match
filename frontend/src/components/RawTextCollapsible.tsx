import { useState } from "react";
import { ChevronDownIcon } from "./ui/icons";

interface Props {
  text: string;
}

export default function RawTextCollapsible({ text }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-panel border border-line rounded-2xl overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center justify-between w-full px-[22px] py-[18px] bg-transparent"
      >
        <span className="text-sm font-semibold tracking-[0.04em] uppercase text-sub">
          Texto original de la oferta
        </span>
        <span className="flex items-center gap-2 text-muted text-[13px] font-normal">
          {expanded ? "Ocultar" : "Mostrar"}
          <span
            className={`w-4 h-4 inline-block transition-transform ${expanded ? "rotate-180" : ""}`}
          >
            <ChevronDownIcon size={16} />
          </span>
        </span>
      </button>
      {expanded && (
        <div className="px-[22px] pb-6">
          <div className="max-h-[340px] overflow-y-auto p-[18px] bg-app border border-hair rounded-[10px] text-[15px] leading-[1.75] text-fg-2 whitespace-pre-wrap">
            {text}
          </div>
        </div>
      )}
    </div>
  );
}
