import { createContext, useContext, useEffect, useState } from "react";

import {
  bootstrapUser,
  getCurrentUser,
  loginUser,
  logoutUser,
} from "@/shared/services/api";
import { clearSessionNavigationContext } from "./sessionNavigation";

const AuthContext = createContext(null);
const DEMO_STORAGE_KEY = "carbono_zero.demo";
const demoUser = {
  id: "demo",
  username: "demo",
  nombre: "Demo Carbono Zero",
  email: "",
  is_demo: true,
  organizaciones: [],
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
    clearSessionNavigationContext();

    const data = await loginUser(payload);
    setUser(data.user || null);
    setHasUsers(true);
    return data;
  };

  const bootstrap = async (payload) => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(DEMO_STORAGE_KEY);
    }
    clearSessionNavigationContext();

    const data = await bootstrapUser(payload);
    setUser(data.user || null);
    setHasUsers(true);
    return data;
  };

  const enterDemo = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(DEMO_STORAGE_KEY, "true");
    }
    clearSessionNavigationContext();

    setUser(demoUser);
    setHasUsers(true);
  };

  const logout = async () => {
    if (user?.is_demo) {
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(DEMO_STORAGE_KEY);
      }
      clearSessionNavigationContext();
      setUser(null);
      return;
    }

    try {
      await logoutUser();
    } finally {
      clearSessionNavigationContext();
      setUser(null);
    }
  };

  const value = {
      bootstrap,
      enterDemo,
      hasUsers,
      loadingAuth,
      login,
      logout,
      refreshAuth,
      user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }

  return context;
}
