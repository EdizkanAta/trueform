import React, { createContext, useContext, useEffect, useState, useCallback } from "react";

import { api, setToken, loadToken } from "@/src/api/client";

export type User = {
  id: string; email: string; dob: string; sex: string; height_cm: number;
  unit_preference: string; onboarded: boolean; has_targets: boolean;
  has_plan: boolean; chosen_target: string | null; base_photo_path: string | null;
  notification_time: string; notifications_enabled: boolean;
  consent: Record<string, boolean>;
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  signup: (payload: any) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<User | null>;
  setUser: (u: User | null) => void;
};

const Ctx = createContext<AuthCtx>({} as AuthCtx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await api.get<User>("/auth/me");
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    (async () => {
      const t = await loadToken();
      if (t) await refresh();
      setLoading(false);
    })();
  }, [refresh]);

  const signup = async (payload: any) => {
    const res = await api.post<{ access_token: string; user: User }>("/auth/signup", payload);
    await setToken(res.access_token);
    setUser(res.user);
  };

  const login = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; user: User }>("/auth/login", { email, password });
    await setToken(res.access_token);
    setUser(res.user);
  };

  const logout = async () => {
    await setToken(null);
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, loading, signup, login, logout, refresh, setUser }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
