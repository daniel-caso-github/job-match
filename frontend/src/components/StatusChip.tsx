import { stateMeta, type RunStatus } from "../lib/pipeline";

export const STATUS_DOT: Record<RunStatus, string> = {
  success: "var(--pos)",
  running: "var(--accent)",
  failed: "var(--neg)",
  queued: "var(--muted)",
};

export default function StatusChip({ status }: { status: RunStatus }) {
  const meta = stateMeta(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold whitespace-nowrap ${meta.bg} ${meta.border} ${meta.fg}`}
    >
      <span className="w-[7px] h-[7px] rounded-full" style={{ background: STATUS_DOT[status] }} />
      {meta.label}
    </span>
  );
}
