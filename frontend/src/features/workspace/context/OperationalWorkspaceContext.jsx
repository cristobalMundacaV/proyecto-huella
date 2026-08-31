import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/shared/services/api";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

const STORAGE_KEY = "carbono_zero.operationalWorkspaceId";
const GENERAL_VIEW = "__general__";
const OperationalWorkspaceContext = createContext(null);

export function OperationalWorkspaceProvider({ children }) {
  const { user } = useAuth();
  const { activeOrganizacionId, setActiveOrganizacion } = useOrganizacionActiva();
  const [state, setState] = useState({ loading: true, workspaces: [], activeId: "", legacy: true });

  useEffect(() => {
    if (!user || user.is_demo) { setState({ loading: false, workspaces: [], activeId: "", legacy: true }); return; }
    let current = true;
    api.get("/contexto-operativo/espacios/").then(({ data }) => {
      if (!current) return;
      const workspaces = activeOrganizacionId
        ? data.workspaces.filter((item) => String(item.organizacion?.id) === String(activeOrganizacionId))
        : data.workspaces;
      const saved = window.localStorage.getItem(STORAGE_KEY) || "";
      const activeId = workspaces.some((item) => String(item.id) === saved)
        ? saved
        : saved === GENERAL_VIEW
          ? ""
          : data.automatico
            ? String(workspaces[0]?.id || "")
            : "";
      if (activeId) window.localStorage.setItem(STORAGE_KEY, activeId);
      else if (saved !== GENERAL_VIEW) window.localStorage.removeItem(STORAGE_KEY);
      setState({ loading: false, workspaces, activeId, legacy: data.legacy });
    }).catch(() => {
      if (!current) return;
      window.localStorage.removeItem(STORAGE_KEY);
      setState({ loading: false, workspaces: [], activeId: "", legacy: true });
    });
    return () => { current = false; };
  }, [activeOrganizacionId, user]);

  const activeWorkspace = useMemo(() => state.workspaces.find((item) => String(item.id) === String(state.activeId)) || null, [state]);
  const selectWorkspace = (workspace) => {
    const id = String(workspace?.id || "");
    setState((current) => ({ ...current, activeId: id }));
    if (id) window.localStorage.setItem(STORAGE_KEY, id); else window.localStorage.removeItem(STORAGE_KEY);
    if (workspace?.organizacion) setActiveOrganizacion({ organizacion_id: workspace.organizacion.id });
  };
  const exitWorkspace = () => {
    setState((current) => ({ ...current, activeId: "" }));
    window.localStorage.setItem(STORAGE_KEY, GENERAL_VIEW);
  };

  useEffect(() => {
    const interceptor = api.interceptors.request.use((config) => {
      if (state.activeId && !config.skipOperationalWorkspace) config.headers["X-Workspace-ID"] = state.activeId;
      return config;
    });
    return () => api.interceptors.request.eject(interceptor);
  }, [state.activeId]);

  return <OperationalWorkspaceContext.Provider value={{ ...state, activeWorkspace, selectWorkspace, exitWorkspace, needsSelection: !state.loading && state.workspaces.length > 1 && !activeWorkspace }}>{children}</OperationalWorkspaceContext.Provider>;
}

export function useOperationalWorkspace() {
  const value = useContext(OperationalWorkspaceContext);
  if (!value) throw new Error("useOperationalWorkspace debe usarse dentro de OperationalWorkspaceProvider");
  return value;
}
