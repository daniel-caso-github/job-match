import { createContext, useContext, useState, type ReactNode } from "react";
import {
  clearCurrentSession,
  getCurrentSession,
  setCurrentSession,
  type ProfileSession,
} from "./profileStorage";

interface ProfileContextValue {
  session: ProfileSession | null;
  /** UUID del perfil activo — es lo que consumen los endpoints de la API. */
  profileId: string | null;
  login: (session: ProfileSession) => void;
  logout: () => void;
}

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<ProfileSession | null>(() => getCurrentSession());

  const login = (next: ProfileSession) => {
    setCurrentSession(next);
    setSession(next);
  };

  const logout = () => {
    clearCurrentSession();
    setSession(null);
  };

  return (
    <ProfileContext.Provider
      value={{ session, profileId: session?.profileId ?? null, login, logout }}
    >
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile(): ProfileContextValue {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be used within ProfileProvider");
  return ctx;
}
