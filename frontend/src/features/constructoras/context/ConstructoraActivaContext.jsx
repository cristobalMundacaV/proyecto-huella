import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getConstructoras } from "@/shared/services/api";

const STORAGE_KEY = "carbono_zero.activeConstructoraId";

const ConstructoraActivaContext = createContext(null);

export function ConstructoraActivaProvider({ children }) {
  const [constructoras, setConstructoras] = useState([]);
  const [activeConstructoraId, setActiveConstructoraId] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }

    return window.localStorage.getItem(STORAGE_KEY) || "";
  });
  const [loadingConstructoras, setLoadingConstructoras] = useState(true);
  const [errorConstructoras, setErrorConstructoras] = useState("");

  const activeConstructora = useMemo(
    () => constructoras.find((constructora) => String(constructora.constructora_id) === String(activeConstructoraId)) || null,
    [activeConstructoraId, constructoras]
  );

  const persistActiveConstructoraId = (constructoraId) => {
    setActiveConstructoraId(constructoraId || "");

    if (typeof window !== "undefined") {
      if (constructoraId) {
        window.localStorage.setItem(STORAGE_KEY, constructoraId);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
  };

  const setActiveConstructora = (constructora) => {
    if (!constructora) {
      clearActiveConstructora();
      return;
    }

    persistActiveConstructoraId(constructora.constructora_id);
  };

  const clearActiveConstructora = () => {
    persistActiveConstructoraId("");
  };

  const refreshConstructoras = async (currentConstructoraId = activeConstructoraId) => {
    setLoadingConstructoras(true);
    setErrorConstructoras("");

    try {
      const data = await getConstructoras();
      const normalized = Array.isArray(data) ? data : data?.results || data?.data || [];

      setConstructoras(normalized);

      if (
        currentConstructoraId &&
        !normalized.some((constructora) => String(constructora.constructora_id) === String(currentConstructoraId))
      ) {
        clearActiveConstructora();
      }

      if (!currentConstructoraId && normalized.length > 0) {
        persistActiveConstructoraId(normalized[0].constructora_id);
      }

      return normalized;
    } catch (error) {
      setErrorConstructoras(error.response?.data?.error || "No se pudieron cargar las empresas.");
      throw error;
    } finally {
      setLoadingConstructoras(false);
    }
  };

  useEffect(() => {
    refreshConstructoras().catch(() => undefined);
  }, []);

  const value = useMemo(
    () => ({
      activeConstructora,
      activeConstructoraId,
      clearActiveConstructora,
      constructoras,
      errorConstructoras,
      loadingConstructoras,
      refreshConstructoras,
      setActiveConstructora,
      setConstructoras,
    }),
    [activeConstructora, activeConstructoraId, constructoras, errorConstructoras, loadingConstructoras]
  );

  return <ConstructoraActivaContext.Provider value={value}>{children}</ConstructoraActivaContext.Provider>;
}

export function useConstructoraActiva() {
  const context = useContext(ConstructoraActivaContext);

  if (!context) {
    throw new Error("useConstructoraActiva debe usarse dentro de ConstructoraActivaProvider");
  }

  return context;
}
