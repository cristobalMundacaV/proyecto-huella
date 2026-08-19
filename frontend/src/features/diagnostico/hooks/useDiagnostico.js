import { useCallback, useEffect, useRef, useState } from "react";

import {
  getCapacidades,
  getDiagnostico,
  getPreparacion,
} from "../api/diagnosticoApi";

const resource = (
  status = "loading",
  data = null,
  error = "",
) => ({
  status,
  data,
  error,
});

export function useDiagnostico(
  organizacionId,
  workId = null,
) {
  const [state, setState] = useState({
    scopeKey: "",
    diagnostico: resource(),
    capacidades: resource("loading", []),
    preparacion: resource(),
  });

  const requestRef = useRef(0);

  const reload = useCallback(async () => {
    if (!organizacionId) {
      return;
    }

    const scopeKey = [
      organizacionId,
      workId || "organizacion",
    ].join(":");

    const requestId = ++requestRef.current;

    setState({
      scopeKey,
      diagnostico: resource(),
      capacidades: resource("loading", []),
      preparacion: resource(),
    });

    const [
      diagnostico,
      capacidades,
      preparacion,
    ] = await Promise.allSettled([
      getDiagnostico(
        organizacionId,
        workId,
      ),
      getCapacidades(
        organizacionId,
      ),
      getPreparacion(
        organizacionId,
      ),
    ]);

    if (
      requestRef.current !==
      requestId
    ) {
      return;
    }

    setState({
      scopeKey,

      diagnostico:
        diagnostico.status ===
          "fulfilled"
          ? resource(
            "ready",
            diagnostico.value,
          )
          : resource(
            "error",
            null,
            diagnostico.reason
              ?.response?.data
              ?.error ||
            diagnostico.reason
              ?.response?.data
              ?.detail ||
            "No se pudo cargar el diagnóstico.",
          ),

      capacidades:
        capacidades.status ===
          "fulfilled"
          ? resource(
            "ready",
            capacidades.value ||
            [],
          )
          : resource(
            "error",
            [],
            capacidades.reason
              ?.response?.data
              ?.error ||
            "No se pudieron cargar las capacidades.",
          ),

      preparacion:
        preparacion.status ===
          "fulfilled"
          ? resource(
            "ready",
            preparacion.value,
          )
          : resource(
            "error",
            null,
            preparacion.reason
              ?.response?.data
              ?.error ||
            "No se pudo cargar el estado de preparación.",
          ),
    });
  }, [
    organizacionId,
    workId,
  ]);

  useEffect(() => {
    reload();

    return () => {
      requestRef.current += 1;
    };
  }, [reload]);

  return {
    ...state,
    reload,
  };
}