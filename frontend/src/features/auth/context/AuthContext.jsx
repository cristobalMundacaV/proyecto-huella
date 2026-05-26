import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  bootstrapUser,
  getCurrentUser,
  loginUser,
  logoutUser,
} from "@/shared/services/api";

const AuthContext = createContext(null);
const DEMO_STORAGE_KEY = "carbono_zero.demo";
const demoUser = {
  id: "demo",
  username: "demo",
  nombre: "Demo Carbono Zero",
  email: "",
  is_demo: true,
  constructoras: [],
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [hasUsers, setHasUsers] = useState(true);
  const [loadingAuth, setLoadingAuth] = useState(true);

  const refreshAuth = async () => {
    if (
      typeof window !== "undefined" &&
      window.localStorage.getItem(DEMO_STORAGE_KEY) === "true"
    ) {
      setUser(demoUser);
      setHasUsers(true);
      return { authenticated: true, user: demoUser, has_users: true };
    }

    const data = await getCurrentUser();
    setUser(data.user || null);
    setHasUsers(Boolean(data.has_users));
    return data;
  };

  useEffect(() => {
    refreshAuth()
      .catch(() => {
        setUser(null);
      })
      .finally(() => setLoadingAuth(false));
  }, []);

  const login = async (payload) => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(DEMO_STORAGE_KEY);
    }

    const data = await loginUser(payload);
    setUser(data.user || null);
    setHasUsers(true);
    return data;
  };

  const bootstrap = async (payload) => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(DEMO_STORAGE_KEY);
    }

    const data = await bootstrapUser(payload);
    setUser(data.user || null);
    setHasUsers(true);
    return data;
  };

  const enterDemo = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(DEMO_STORAGE_KEY, "true");
    }

    setUser(demoUser);
    setHasUsers(true);
  };

  const logout = async () => {
    if (user?.is_demo) {
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(DEMO_STORAGE_KEY);
      }
      setUser(null);
      return;
    }

    await logoutUser();
    setUser(null);
  };

  const value = useMemo(
    () => ({
      bootstrap,
      enterDemo,
      hasUsers,
      loadingAuth,
      login,
      logout,
      refreshAuth,
      user,
    }),
    [hasUsers, loadingAuth, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }

  return context;
}
