import { useEffect, useRef, useState } from "react";
import { CheckIcon, ChevronDownIcon, XIcon } from "./icons";

interface MultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  loading?: boolean;
}

export default function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Seleccionar",
  searchPlaceholder = "buscar",
  loading = false,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (option: string) => {
    onChange(
      selected.includes(option)
        ? selected.filter((s) => s !== option)
        : [...selected, option],
    );
  };

  const visible = options.filter((o) => o.includes(query.trim().toLowerCase()));

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 w-full min-h-9 px-2.5 py-1.5 bg-app border rounded-[9px] text-left transition-colors ${
          open ? "border-accent" : "border-line-2"
        } ${loading ? "animate-pulse" : ""}`}
      >
        <span className="flex-1 flex flex-wrap gap-1 min-w-0">
          {selected.length === 0 ? (
            <span className="text-[13px] text-muted">
              {loading ? "Cargando…" : placeholder}
            </span>
          ) : (
            selected.map((item) => (
              <span
                key={item}
                className="inline-flex items-center gap-1 pl-1.5 pr-1 py-0.5 bg-accent-soft border border-accent-line rounded-md font-mono text-[11px] text-accent-text"
              >
                {item}
                <span
                  role="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggle(item);
                  }}
                  className="flex text-muted hover:text-neg transition-colors"
                >
                  <XIcon size={10} />
                </span>
              </span>
            ))
          )}
        </span>
        <span
          className={`w-3.5 h-3.5 shrink-0 text-muted transition-transform ${
            open ? "rotate-180" : ""
          }`}
        >
          <ChevronDownIcon size={14} />
        </span>
      </button>

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 z-20 bg-panel border border-line-2 rounded-[10px] shadow-[0_8px_24px_rgba(0,0,0,0.25)] overflow-hidden">
          <div className="p-2 border-b border-hair">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full h-8 px-2.5 bg-app border border-line-2 rounded-[7px] text-fg font-mono text-[13px] outline-none focus:border-accent"
            />
          </div>
          <div className="max-h-[240px] overflow-y-auto py-1">
            {visible.map((option) => {
              const isSelected = selected.includes(option);
              return (
                <button
                  key={option}
                  type="button"
                  onClick={() => toggle(option)}
                  className={`flex items-center justify-between gap-2 w-full px-3 py-1.5 font-mono text-xs text-left hover:bg-panel2 transition-colors ${
                    isSelected ? "text-accent-text" : "text-fg-2"
                  }`}
                >
                  {option}
                  {isSelected && (
                    <span className="w-3.5 h-3.5 shrink-0 text-accent-text">
                      <CheckIcon size={14} />
                    </span>
                  )}
                </button>
              );
            })}
            {visible.length === 0 && (
              <p className="m-0 px-3 py-2 text-[13px] text-muted">Sin resultados.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
