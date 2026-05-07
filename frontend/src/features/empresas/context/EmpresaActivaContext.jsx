import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getEmpresas } from "@/shared/services/api";

const STORAGE_KEY = "huella.activeEmpresaId";

const EmpresaActivaContext = createContext(null);

export function EmpresaActivaProvider({ children }) {
  const [empresas, setEmpresas] = useState([]);
  const [activeEmpresaId, setActiveEmpresaId] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }

    return window.localStorage.getItem(STORAGE_KEY) || "";
  });
  const [loadingEmpresas, setLoadingEmpresas] = useState(true);
  const [errorEmpresas, setErrorEmpresas] = useState("");

  const activeEmpresa = useMemo(
    () => empresas.find((empresa) => String(empresa.empresa_id) === String(activeEmpresaId)) || null,
    [activeEmpresaId, empresas]
  );

  const persistActiveEmpresaId = (empresaId) => {
    setActiveEmpresaId(empresaId || "");

    if (typeof window !== "undefined") {
      if (empresaId) {
        window.localStorage.setItem(STORAGE_KEY, empresaId);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
  };

  const setActiveEmpresa = (empresa) => {
    if (!empresa) {
      clearActiveEmpresa();
      return;
    }

    persistActiveEmpresaId(empresa.empresa_id);
  };

  const clearActiveEmpresa = () => {
    persistActiveEmpresaId("");
  };

  const refreshEmpresas = async () => {
    setLoadingEmpresas(true);
    setErrorEmpresas("");

    try {
      const data = await getEmpresas();

      const normalized = Array.isArray(data)
        ? data
        : data?.results || data?.data || [];

      setEmpresas(normalized);

      if (
        activeEmpresaId &&
        !normalized.some((empresa) => String(empresa.empresa_id) === String(activeEmpresaId))
      ) {
        clearActiveEmpresa();
      }

      return normalized;
    } catch (error) {
      setErrorEmpresas(error.response?.data?.error || "No se pudieron cargar las empresas.");
      throw error;
    } finally {
      setLoadingEmpresas(false);
    }
  };

  useEffect(() => {
    refreshEmpresas().catch(() => undefined);
  }, []);

  const value = useMemo(
    () => ({
      activeEmpresa,
      activeEmpresaId,
      clearActiveEmpresa,
      refreshEmpresas,
      empresas,
      errorEmpresas,
      loadingEmpresas,
      setActiveEmpresa,
      setEmpresas,
    }),
    [activeEmpresa, activeEmpresaId, empresas, errorEmpresas, loadingEmpresas]
  );

  return <EmpresaActivaContext.Provider value={value}>{children}</EmpresaActivaContext.Provider>;
}

export function useEmpresaActiva() {
  const context = useContext(EmpresaActivaContext);

  if (!context) {
    throw new Error("useEmpresaActiva debe usarse dentro de EmpresaActivaProvider");
  }

  return context;
}
