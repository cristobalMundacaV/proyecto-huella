import { useCallback, useEffect, useState } from "react";
import { getCapacidades, getDiagnostico, getPreparacion, getProcesos, getUnidades } from "../api/diagnosticoApi";

export function useDiagnostico(organizacionId) {
  const [data, setData] = useState({ diagnostico: null, capacidades: [], unidades: [], procesos: [], preparacion: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    if (!organizacionId) return;
    setLoading(true); setError("");
    try {
      const [diagnostico, capacidades, unidades, procesos, preparacion] = await Promise.all([
        getDiagnostico(organizacionId), getCapacidades(organizacionId), getUnidades(organizacionId), getProcesos(organizacionId), getPreparacion(organizacionId),
      ]);
      setData({ diagnostico, capacidades, unidades, procesos, preparacion });
    } catch (e) { setError(e?.response?.data?.error || "No se pudo cargar la preparación ambiental."); }
    finally { setLoading(false); }
  }, [organizacionId]);
  useEffect(() => { reload(); }, [reload]);
  return { ...data, loading, error, reload };
}
