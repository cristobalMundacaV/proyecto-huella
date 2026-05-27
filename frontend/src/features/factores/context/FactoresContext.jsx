import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getFactoresEmision } from "@/shared/services/api";

const FactoresContext = createContext(null);

function normalizeFactor(factor) {
  return {
    ...factor,
    fuente_emision: factor?.fuente_emision || factor?.actividad || factor?.nombre || "Fuente sin nombre",
    fuente_emision_key: factor?.fuente_emision_key || factor?.actividad_key || "",
    categoria: factor?.categoria || "Otros",
    unidad: factor?.unidad || "-",
    factor_emision: factor?.factor_emision ?? factor?.factor ?? 0,
    anio: factor?.anio || "-",
  };
}

function normalizeFactorResponse(data) {
  const rows = Array.isArray(data)
    ? data
    : Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data?.data)
        ? data.data
        : Array.isArray(data?.factores)
          ? data.factores
          : [];

  return rows.map(normalizeFactor);
}

export function FactoresProvider({ children }) {
  const [factores, setFactores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refreshFactores = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getFactoresEmision();
      const normalized = normalizeFactorResponse(data);
      setFactores(normalized);
      return normalized;
    } catch (requestError) {
      setFactores([]);
      setError(
        requestError.response?.data?.error ||
          "No se pudieron cargar los factores de emisión."
      );
      throw requestError;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshFactores().catch(() => undefined);
  }, [refreshTrigger]);

  const value = useMemo(
    () => ({
      factores,
      loading,
      error,
      refreshFactores,
      invalidate: () => setRefreshTrigger((prev) => prev + 1),
    }),
    [factores, loading, error]
  );

  return (
    <FactoresContext.Provider value={value}>{children}</FactoresContext.Provider>
  );
}

export function useFactores() {
  const context = useContext(FactoresContext);

  if (!context) {
    throw new Error("useFactores debe usarse dentro de FactoresProvider");
  }

  return context;
}
