export interface ProfileSession {
  profileId: string;
  username: string;
  token: string;
}

const KEY = "jobmatch.profile";

// Keys legacy (pre-UUID) — guardaban el slug pelado, que ya no sirve como profile_id.
const LEGACY_KEYS = ["jobmatch.profileId", "jobmatch.lastProfileId", "jobmatch.lastProfile"];

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function parseSession(raw: string | null): ProfileSession | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<ProfileSession>;
    if (
      typeof parsed.profileId === "string" &&
      UUID_RE.test(parsed.profileId) &&
      typeof parsed.username === "string" &&
      parsed.username.length > 0 &&
      typeof parsed.token === "string" &&
      parsed.token.length > 0
    ) {
      return { profileId: parsed.profileId, username: parsed.username, token: parsed.token };
    }
  } catch {
    // valor corrupto/legacy — se descarta abajo
  }
  return null;
}

export function getCurrentSession(): ProfileSession | null {
  LEGACY_KEYS.forEach((k) => localStorage.removeItem(k));
  const session = parseSession(localStorage.getItem(KEY));
  if (session === null) localStorage.removeItem(KEY);
  return session;
}

export function setCurrentSession(session: ProfileSession): void {
  localStorage.setItem(KEY, JSON.stringify(session));
}

export function clearCurrentSession(): void {
  localStorage.removeItem(KEY);
}

