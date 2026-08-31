import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Outlet,
  useOutletContext,
} from "react-router-dom";

import {
  useOrganizacionActiva,
} from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  ErrorState,
} from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";

import {
  getWorkOperation,
} from "../services/operationApi";

export default function OperationLayout() {
  const workspace =
    useOutletContext();

  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const workId =
    workspace.obra.id ||
    workspace.obra.obra_id;

  const [
    state,
    setState,
  ] = useState({
    status: "loading",
    data: null,
  });

  const requestRef =
    useRef(0);

  const load =
    useCallback(() => {
      if (
        !activeOrganizacionId ||
        !workId
      ) {
        return;
      }

      const requestId =
        ++requestRef.current;

      setState({
        status: "loading",
        data: null,
      });

      getWorkOperation(
        activeOrganizacionId,
        workId
      )
        .then(data => {
          if (
            requestRef.current ===
            requestId
          ) {
            setState({
              status: "ready",
              data,
            });
          }
        })
        .catch(() => {
          if (
            requestRef.current ===
            requestId
          ) {
            setState({
              status: "error",
              data: null,
            });
          }
        });
    }, [
      activeOrganizacionId,
      workId,
    ]);

  useEffect(() => {
    load();

    return () => {
      requestRef.current += 1;
    };
  }, [
    load,
  ]);

  if (
    state.status ===
    "loading"
  ) {
    return (
      <PlatformLoader title="Cargando operación" description="Estamos reuniendo actividad, mediciones y trazabilidad de esta obra." />
    );
  }

  if (
    state.status ===
    "error"
  ) {
    return (
      <ErrorState
        description="No fue posible preparar la información operacional de esta unidad."
        onRetry={load}
      />
    );
  }

  return (
    <Outlet
      context={{
        ...workspace,
        indicators: state.data.sectorIndicators.status === "ready"
          ? {
            flujos: state.data.sectorIndicators.data?.indicadores || [],
            totales_compatibles: state.data.sectorIndicators.data?.totales_compatibles || [],
          }
          : { flujos: [], totales_compatibles: [] },
        resourceErrors: {
          ...workspace.resourceErrors,
          indicators: state.data.sectorIndicators.status !== "ready",
        },
        operation:
          state.data,
        reloadOperation:
          load,
      }}
    />
  );
}
