import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  bootstrapUser,
  getCurrentUser,
  loginUser,
  logoutUser,
} from "@/shared/services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [hasUsers, setHasUsers] = useState(true);
  const [loadingAuth, setLoadingAuth] = useState(true);

  const refreshAuth = async () => {
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
    const data = await loginUser(payload);
    setUser(data.user || null);
    setHasUsers(true);
    return data;
  };

  const bootstrap = async (payload) => {
    const data = await bootstrapUser(payload);
    setUser(data.user || null);
    setHasUsers(true);
    return data;
  };

  const logout = async () => {
    await logoutUser();
    setUser(null);
  };

  const value = useMemo(
    () => ({
      bootstrap,
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
