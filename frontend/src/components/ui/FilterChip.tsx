import type { ReactNode } from "react";

interface FilterChipProps {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
  dot?: string;
}

export default function FilterChip({ active, onClick, children, dot }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-[7px] px-[13px] py-[7px] rounded-[9px] border text-sm font-medium transition-colors ${
        active
          ? "bg-accent-soft border-accent-line text-accent-text"
          : "bg-panel border-line-2 text-sub"
      }`}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full" style={{ background: dot }} />}
      {children}
    </button>
  );
}
