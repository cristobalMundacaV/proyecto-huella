import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getOrganizaciones } from "@/shared/services/api";

const STORAGE_KEY = "carbono_zero.activeOrganizacionId";

const OrganizacionActivaContext = createContext(null);

export function OrganizacionActivaProvider({ children }) {
  const [organizaciones, setOrganizaciones] = useState([]);
  const [activeOrganizacionId, setActiveOrganizacionId] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }

    return window.localStorage.getItem(STORAGE_KEY) || "";
  });
  const [loadingOrganizaciones, setLoadingOrganizaciones] = useState(true);
  const [errorOrganizaciones, setErrorOrganizaciones] = useState("");

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
    setLoadingOrganizaciones(true);
    setErrorOrganizaciones("");

    try {
      const data = await getOrganizaciones();
      const normalized = Array.isArray(data) ? data : data?.results || data?.data || [];

      setOrganizaciones(normalized);

      if (
        currentOrganizacionId &&
        !normalized.some((organizacion) => String(organizacion.organizacion_id) === String(currentOrganizacionId))
      ) {
        clearActiveOrganizacion();
      }

      if (!currentOrganizacionId && normalized.length === 1) {
        persistActiveOrganizacionId(normalized[0].organizacion_id);
      }

      return normalized;
    } catch (error) {
      setErrorOrganizaciones(error.response?.data?.error || "No se pudieron cargar las empresas.");
      throw error;
    } finally {
      setLoadingOrganizaciones(false);
    }
  };

  useEffect(() => {
    refreshOrganizaciones().catch(() => undefined);
    // La carga inicial se ejecuta una vez; refresh usa el ID persistido vigente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = {
      activeOrganizacion,
      activeOrganizacionId,
      clearActiveOrganizacion,
      organizaciones,
      errorOrganizaciones,
      loadingOrganizaciones,
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
