import { sourceMeta } from "../lib/score";

export default function SourceBadge({ source }: { source: string }) {
  const meta = sourceMeta(source);
  return (
    <span
      className="inline-flex items-center gap-[5px] px-2 py-0.5 bg-chip border border-line-2 rounded-md text-xs font-medium"
      style={{ color: meta.text }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: meta.dot }} />
      {meta.label}
    </span>
  );
}
