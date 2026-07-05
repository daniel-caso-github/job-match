export interface ScoreColor {
  text: string;
  fg: string;
  bg: string;
  border: string;
}

export function scoreColors(score: number | null | undefined): ScoreColor {
  if (score === null || score === undefined)
    return { text: "—", fg: "text-score-none", bg: "bg-score-none-soft", border: "border-score-none-line" };
  const s = Math.round(score);
  if (s >= 70)
    return { text: String(s), fg: "text-score-green", bg: "bg-score-green-soft", border: "border-score-green-line" };
  if (s >= 40)
    return { text: String(s), fg: "text-score-amber", bg: "bg-score-amber-soft", border: "border-score-amber-line" };
  return { text: String(s), fg: "text-score-red", bg: "bg-score-red-soft", border: "border-score-red-line" };
}

export interface SourceMeta {
  label: string;
  dot: string;
  text: string;
}

const SOURCE_META: Record<string, SourceMeta> = {
  himalayas: { label: "Himalayas", dot: "var(--src-him-dot)", text: "var(--src-him-text)" },
  remotive: { label: "Remotive", dot: "var(--src-rem-dot)", text: "var(--src-rem-text)" },
  jobicy: { label: "Jobicy", dot: "var(--src-jcy-dot)", text: "var(--src-jcy-text)" },
  remoteok: { label: "RemoteOK", dot: "var(--src-rok-dot)", text: "var(--src-rok-text)" },
  arbeitnow: { label: "Arbeitnow", dot: "var(--src-abn-dot)", text: "var(--src-abn-text)" },
  adzuna: { label: "Adzuna", dot: "var(--src-azn-dot)", text: "var(--src-azn-text)" },
  jooble: { label: "Jooble", dot: "var(--src-jbl-dot)", text: "var(--src-jbl-text)" },
};

export function sourceMeta(source: string): SourceMeta {
  return SOURCE_META[source] ?? { label: source, dot: "var(--muted)", text: "var(--text2)" };
}
