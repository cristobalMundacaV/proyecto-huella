import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getFactoresEmision } from "@/shared/services/api";

const FactoresContext = createContext(null);

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
      setFactores(data);
      return data;
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "No se pudieron cargar los factores de emision."
      );
      throw requestError;
    } finally {
      setLoading(false);
    }
  };

  // Initial load and reload on trigger
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
