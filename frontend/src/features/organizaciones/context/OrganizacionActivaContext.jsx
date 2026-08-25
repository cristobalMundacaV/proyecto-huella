import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { getOrganizaciones } from "@/shared/services/api";

import { createOrganizationRequestTracker } from "./organizationRequestTracker";
import { resolveActiveOrganizationId } from "./organizationResolution";

const STORAGE_KEY = "carbono_zero.activeOrganizacionId";
const OrganizacionActivaContext = createContext(null);
const initialResolution = { status: "idle", organizations: [], error: "", identityId: "" };

export function OrganizacionActivaProvider({ children }) {
  const { loadingAuth, user } = useAuth();
  const [resolution, setResolution] = useState(initialResolution);
  const [activeOrganizacionId, setActiveOrganizacionId] = useState(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(STORAGE_KEY) || "";
  });
  const requestTrackerRef = useRef(null);
  if (requestTrackerRef.current === null) requestTrackerRef.current = createOrganizationRequestTracker();

  const currentIdentityId = user ? String(user.id ?? user.username ?? "authenticated") : "";
  const organizaciones = resolution.organizations;
  const organizationResolutionStatus = resolution.status;
  const loadingOrganizaciones = organizationResolutionStatus === "loading";
  const resolvingOrganizations = loadingOrganizaciones;
  const errorOrganizaciones = resolution.error;

  const activeOrganizacion = useMemo(
    () => organizaciones.find((item) => String(item.organizacion_id) === String(activeOrganizacionId)) || null,
    [activeOrganizacionId, organizaciones],
  );

  const persistActiveOrganizacionId = (organizacionId) => {
    const normalizedId = String(organizacionId || "");
    setActiveOrganizacionId(normalizedId);
    if (typeof window === "undefined") return;
    if (normalizedId) window.localStorage.setItem(STORAGE_KEY, normalizedId);
    else window.localStorage.removeItem(STORAGE_KEY);
  };

  const setActiveOrganizacion = (organizacion) => {
    if (!organizacion) {
      const onlyOrganization = resolution.organizations.length === 1 ? resolution.organizations[0] : null;
      persistActiveOrganizacionId(onlyOrganization?.organizacion_id || "");
      setResolution((current) => ({
        ...current,
        status: current.organizations.length > 1 ? "selection_required" : current.organizations.length === 1 ? "ready" : "empty",
      }));
      return;
    }
    persistActiveOrganizacionId(organizacion.organizacion_id);
    setResolution((current) => ({ ...current, status: "ready", error: "" }));
  };

  const clearActiveOrganizacion = () => setActiveOrganizacion(null);

  const refreshOrganizaciones = async (preferredOrganizationId = activeOrganizacionId) => {
    const tracker = requestTrackerRef.current;
    const { requestId, signal } = tracker.start();
    const identityId = currentIdentityId;
    setResolution((current) => ({ ...current, status: "loading", error: "", identityId }));

    try {
      const data = await getOrganizaciones({ signal, timeout: 20000 });
      const normalized = Array.isArray(data) ? data : data?.results || data?.data || [];
      if (!tracker.isCurrent(requestId)) return normalized;

      const resolvedId = resolveActiveOrganizationId(normalized, preferredOrganizationId);
      persistActiveOrganizacionId(resolvedId);
      setResolution({
        status: normalized.length === 0 ? "empty" : resolvedId ? "ready" : "selection_required",
        organizations: normalized,
        error: "",
        identityId,
      });
      return normalized;
    } catch (error) {
      if (!tracker.isCurrent(requestId)) return [];
      setResolution({
        status: "error",
        organizations: [],
        error: error.response?.data?.error || error.response?.data?.detail || "No pudimos cargar tu organización. Inténtalo nuevamente.",
        identityId,
      });
      throw error;
    } finally {
      if (tracker.isCurrent(requestId)) {
        setResolution((current) => current.status === "loading"
          ? { ...current, status: "error", error: current.error || "No pudimos completar la resolución de tu organización." }
          : current);
      }
    }
  };

  useEffect(() => {
    if (loadingAuth) {
      requestTrackerRef.current.invalidate();
      setResolution(initialResolution);
      return;
    }
    if (!user || user.is_demo) {
      requestTrackerRef.current.invalidate();
      persistActiveOrganizacionId("");
      setResolution({ ...initialResolution, status: "empty", identityId: currentIdentityId });
      return;
    }

    const persistedId = typeof window === "undefined" ? "" : window.localStorage.getItem(STORAGE_KEY) || "";
    persistActiveOrganizacionId("");
    setResolution({ ...initialResolution, status: "loading", identityId: currentIdentityId });
    refreshOrganizaciones(persistedId).catch(() => undefined);
    return () => requestTrackerRef.current.invalidate();
    // La identidad autenticada es la única dependencia que inicia una resolución completa.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIdentityId, loadingAuth, user?.is_demo]);

  const value = {
    activeOrganizacion,
    activeOrganizacionId,
    clearActiveOrganizacion,
    organizaciones,
    errorOrganizaciones,
    loadingOrganizaciones,
    organizationResolutionStatus,
    refreshOrganizaciones,
    resolvingOrganizations,
    setActiveOrganizacion,
  };
  return <OrganizacionActivaContext.Provider value={value}>{children}</OrganizacionActivaContext.Provider>;
}

export function useOrganizacionActiva() {
  const context = useContext(OrganizacionActivaContext);
  if (!context) throw new Error("useOrganizacionActiva debe usarse dentro de OrganizacionActivaProvider");
  return context;
}
