const rtf = new Intl.RelativeTimeFormat("es", { numeric: "auto" });
const dtf = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });
const tf = new Intl.DateTimeFormat("es", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

export function formatDateTime(iso: string | null): string {
  return iso ? dtf.format(new Date(iso)) : "—";
}

export function formatTime(iso: string | null): string {
  return iso ? tf.format(new Date(iso)) : "—";
}

export function relativeTime(iso: string | null): string {
  if (!iso) return "pendiente";
  const diffMinutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (diffMinutes < 60) return rtf.format(-diffMinutes, "minute");
  const hours = Math.round(diffMinutes / 60);
  if (hours < 24) return rtf.format(-hours, "hour");
  return rtf.format(-Math.round(hours / 24), "day");
}

export function relativeTimeTo(iso: string | null): string | null {
  if (!iso) return null;
  const diffMinutes = Math.round((new Date(iso).getTime() - Date.now()) / 60_000);
  if (diffMinutes <= 0) return null;
  if (diffMinutes < 60) return rtf.format(diffMinutes, "minute");
  const hours = Math.round(diffMinutes / 60);
  if (hours < 24) return rtf.format(hours, "hour");
  return rtf.format(Math.round(hours / 24), "day");
}

export function formatSemantic(score: number | null): string {
  return score === null ? "sin score" : score.toFixed(3);
}

export function safeHref(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? url : undefined;
  } catch {
    return undefined;
  }
}
