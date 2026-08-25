import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import { getOrganizaciones } from "@/shared/services/api";
import { useAuth } from "@/features/auth/context/AuthContext";
import { resolveActiveOrganizationId } from "./organizationResolution";
import { createOrganizationRequestTracker } from "./organizationRequestTracker";

const STORAGE_KEY = "carbono_zero.activeOrganizacionId";

const OrganizacionActivaContext = createContext(null);

export function OrganizacionActivaProvider({ children }) {
  const { loadingAuth, user } = useAuth();
  const [organizaciones, setOrganizaciones] = useState([]);
  const [activeOrganizacionId, setActiveOrganizacionId] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }

    return window.localStorage.getItem(STORAGE_KEY) || "";
  });
  const [loadingOrganizaciones, setLoadingOrganizaciones] = useState(true);
  const [errorOrganizaciones, setErrorOrganizaciones] = useState("");
  const [resolvedIdentityId, setResolvedIdentityId] = useState("");
  const requestTrackerRef = useRef(null);
  if (requestTrackerRef.current === null) {
    requestTrackerRef.current = createOrganizationRequestTracker();
  }
  const currentIdentityId = user ? String(user.id ?? user.username ?? "authenticated") : "";
  const resolvingOrganizations = loadingAuth || loadingOrganizaciones || Boolean(user && !user.is_demo && resolvedIdentityId !== currentIdentityId);

  const activeOrganizacion = useMemo(
    () => organizaciones.find((organizacion) => String(organizacion.organizacion_id) === String(activeOrganizacionId)) || null,
    [activeOrganizacionId, organizaciones]
  );

  const persistActiveOrganizacionId = (organizacionId) => {
    setActiveOrganizacionId(organizacionId || "");

    if (typeof window !== "undefined") {
      if (organizacionId) {
        window.localStorage.setItem(STORAGE_KEY, organizacionId);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
  };

  const setActiveOrganizacion = (organizacion) => {
    if (!organizacion) {
      clearActiveOrganizacion();
      return;
    }

    persistActiveOrganizacionId(organizacion.organizacion_id);
  };

  const clearActiveOrganizacion = () => {
    persistActiveOrganizacionId("");
  };

  const refreshOrganizaciones = async (currentOrganizacionId = activeOrganizacionId) => {
    const tracker = requestTrackerRef.current;
    const { requestId, signal } = tracker.start();
    const identityId = currentIdentityId;
    setLoadingOrganizaciones(true);
    setErrorOrganizaciones("");

    try {
      const data = await getOrganizaciones({ signal, timeout: 20000 });
      const normalized = Array.isArray(data) ? data : data?.results || data?.data || [];
      if (!tracker.isCurrent(requestId)) return normalized;

      setOrganizaciones(normalized);

      const resolvedId = resolveActiveOrganizationId(normalized, currentOrganizacionId);
      if (String(activeOrganizacionId || "") !== resolvedId) persistActiveOrganizacionId(resolvedId);
      setResolvedIdentityId(identityId);

      return normalized;
    } catch (error) {
      if (!tracker.isCurrent(requestId)) return [];
      setErrorOrganizaciones(error.response?.data?.error || error.response?.data?.detail || "No pudimos cargar tu organización. Inténtalo nuevamente.");
      setResolvedIdentityId(identityId);
      throw error;
    } finally {
      if (tracker.isCurrent(requestId)) setLoadingOrganizaciones(false);
    }
  };

  useEffect(() => {
    if (loadingAuth) return;
    if (!user || user.is_demo) {
      requestTrackerRef.current.invalidate();
      setOrganizaciones([]);
      persistActiveOrganizacionId("");
      setErrorOrganizaciones("");
      setResolvedIdentityId(currentIdentityId);
      setLoadingOrganizaciones(false);
      return;
    }
    const persistedId = typeof window === "undefined" ? "" : window.localStorage.getItem(STORAGE_KEY) || "";
    setResolvedIdentityId("");
    setLoadingOrganizaciones(true);
    setOrganizaciones([]);
    persistActiveOrganizacionId("");
    refreshOrganizaciones(persistedId).catch(() => undefined);
    return () => requestTrackerRef.current.invalidate();
    // La fuente de verdad se recarga cada vez que cambia la identidad autenticada.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingAuth, user?.id]);

  const value = {
      activeOrganizacion,
      activeOrganizacionId,
      clearActiveOrganizacion,
      organizaciones,
      errorOrganizaciones,
      loadingOrganizaciones,
      resolvingOrganizations,
      refreshOrganizaciones,
      setActiveOrganizacion,
      setOrganizaciones,
  };

  return <OrganizacionActivaContext.Provider value={value}>{children}</OrganizacionActivaContext.Provider>;
}

export function useOrganizacionActiva() {
  const context = useContext(OrganizacionActivaContext);

  if (!context) {
    throw new Error("useOrganizacionActiva debe usarse dentro de OrganizacionActivaProvider");
  }

  return context;
}
