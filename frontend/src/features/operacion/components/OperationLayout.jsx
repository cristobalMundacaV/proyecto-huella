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
  LoadingState,
} from "@/shared/ui";

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
      <LoadingState label="Cargando información operacional" />
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
        operation:
          state.data,
        reloadOperation:
          load,
      }}
    />
  );
}