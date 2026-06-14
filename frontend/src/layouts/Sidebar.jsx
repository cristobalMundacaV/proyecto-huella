import { useState } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Building2,
  Database,
  DatabaseZap,
  Factory,
  FileCheck2,
  Flame,
  LayoutDashboard,
  Loader2,
  LogOut,
  Settings,
  Trash2,
  UsersRound,
  X,
} from "lucide-react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { getActivePreset, getPresetLabel } from "@/presets/registry";
import { deleteEmpresa } from "@/shared/services/api";

const navigationIconMap = {
  dashboard: LayoutDashboard,
  emisiones: Flame,
  factores: Database,
  constructoras: Building2,
  obras: Boxes,
  etapas: Factory,
  evidencias: FileCheck2,
  importaciones: DatabaseZap,
  reportes: BarChart3,
  usuarios: UsersRound,
  configuracion: Settings,
  recepcion_trozas: Database,
  produccion: Factory,
  secado: Flame,
  energia: DatabaseZap,
  transporte_forestal: Factory,
  residuos_subproductos: Boxes,
  flota: Factory,
  viajes: BarChart3,
  combustible: Flame,
  rutas: Database,
  mantenciones: Settings,
};

function Sidebar({ activeView, onSetActiveView, systemStatus }) {
  const { logout, user } = useAuth();
  const {
    activeConstructora,
    activeConstructoraId,
    clearActiveConstructora,
    constructoras,
    loadingConstructoras,
    refreshConstructoras,
    setActiveConstructora,
  } = useConstructoraActiva();
  const activePresetKey = activeConstructora?.preset || "construccion";
  const activePreset = getActivePreset(activePresetKey);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const navigationItems = (activePreset.navigation || []).map((item) => ({
    ...item,
    icon: navigationIconMap[item.view] || LayoutDashboard,
  }));
  const statusItems = [
    [activePreset.processPluralLabel, systemStatus?.etapas ?? 0],
    [activePreset.unitPluralLabel, systemStatus?.obras ?? 0],
    ["Registros", systemStatus?.registros_emision ?? 0],
    ["Evidencias", systemStatus?.evidencias ?? 0],
    ["Fichas", systemStatus?.fichas_ambientales ?? 0],
  ];

  const selectedConstructora =
    activeConstructora ||
    constructoras.find((constructora) => String(constructora.constructora_id) === String(activeConstructoraId)) ||
    null;
  const deleteToken = selectedConstructora?.constructora_id || selectedConstructora?.nombre || "";
  const canConfirmDelete = Boolean(deleteToken) && deleteConfirmText.trim() === String(deleteToken).trim();

  const closeDeleteModal = () => {
    if (deleting) return;
    setDeleteModalOpen(false);
    setDeleteConfirmText("");
    setDeleteError("");
  };

  const handleDeleteConstructora = async () => {
    if (!selectedConstructora || !canConfirmDelete) return;

    setDeleting(true);
    setDeleteError("");

    try {
      const deletedId = selectedConstructora.constructora_id;
      await deleteEmpresa(deletedId);
      const updatedConstructoras = await refreshConstructoras(deletedId);
      const nextConstructora = updatedConstructoras.find(
        (constructora) => String(constructora.constructora_id) !== String(deletedId)
      );

      if (nextConstructora) {
        setActiveConstructora(nextConstructora);
      } else {
        clearActiveConstructora();
      }

      setDeleteModalOpen(false);
      setDeleteConfirmText("");
      onSetActiveView?.("constructoras");
    } catch (error) {
      setDeleteError(
        error.response?.data?.error ||
          "No se pudo eliminar la empresa. Revisa si tiene datos relacionados o intenta nuevamente."
      );
    } finally {
      setDeleting(false);
    }
  };

  const deleteModal =
    deleteModalOpen && selectedConstructora
      ? createPortal(
          <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/60 px-4 py-6 backdrop-blur-sm">
            <div className="relative z-[10000] w-full max-w-lg rounded-3xl border border-red-200 bg-white p-6 text-slate-950 shadow-[0_28px_90px_rgba(15,23,42,0.35)]">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-red-200 bg-red-50 text-red-600">
                    <AlertTriangle size={24} />
                  </div>
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.16em] text-red-700">
                      Acción irreversible
                    </p>
                    <h2 className="mt-1 text-2xl font-black text-slate-950">
                      Eliminar empresa
                    </h2>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={closeDeleteModal}
                  className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50"
                >
                  <X size={18} />
                </button>
              </div>

              <p className="mt-5 text-sm font-medium leading-7 text-slate-600">
                Se eliminará <strong className="text-slate-950">{selectedConstructora.nombre}</strong> junto con sus datos relacionados. Esta acción sirve para limpiar empresas de prueba, pero no se puede deshacer desde la interfaz.
              </p>

              <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
                Para confirmar, escribe exactamente:
                <span className="mt-2 block rounded-xl border border-red-200 bg-white px-3 py-2 font-black text-red-800">
                  {deleteToken}
                </span>
              </div>

              <input
                value={deleteConfirmText}
                onChange={(event) => setDeleteConfirmText(event.target.value)}
                placeholder="Escribe el ID de la empresa"
                className="mt-4 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-red-300 focus:ring-4 focus:ring-red-100"
              />

              {deleteError && (
                <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
                  {deleteError}
                </p>
              )}

              <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={closeDeleteModal}
                  className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-black text-slate-600 transition hover:bg-slate-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleDeleteConstructora}
                  disabled={!canConfirmDelete || deleting}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-red-700 bg-red-600 px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(220,38,38,0.22)] transition hover:-translate-y-0.5 hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {deleting ? <Loader2 className="animate-spin" size={17} /> : <Trash2 size={17} />}
                  Eliminar definitivamente
                </button>
              </div>
            </div>
          </div>,
          document.body
        )
      : null;

  return (
    <aside className="w-full shrink-0 border-b border-white/10 bg-[var(--sidebar)] p-4 text-slate-100 shadow-[24px_0_80px_rgba(2,6,23,0.22)] sm:p-6 lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-72 lg:flex-col lg:border-b-0 lg:border-r lg:overflow-y-auto">
      <div className="mb-10 flex items-center gap-3">
        <div className="rounded-2xl border border-emerald-300/20 bg-[linear-gradient(180deg,rgba(18,61,52,1),rgba(15,45,39,0.96))] p-3 shadow-[0_16px_30px_rgba(0,0,0,0.24)] ring-1 ring-emerald-200/10">
          <Database className="text-emerald-300" />
        </div>
        <div>
          <h2 className="text-xl font-black tracking-tight">Carbono Zero</h2>
          <p className="text-xs text-slate-400">Inteligencia ambiental por rubro</p>
        </div>
      </div>

      <section className="group mb-8 rounded-2xl border border-emerald-300/15 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03))] p-4 shadow-[0_12px_28px_rgba(0,0,0,0.14)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/40 hover:shadow-[0_18px_36px_rgba(0,0,0,0.2)]">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 transition group-hover:text-emerald-200">
          Empresa activa
        </p>
        <div className="mt-3 space-y-3">
          <select
            value={activeConstructoraId}
            onChange={(event) => {
              const selected = constructoras.find(
                (constructora) => String(constructora.constructora_id) === String(event.target.value)
              );

              if (selected) {
                setActiveConstructora(selected);
              } else {
                clearActiveConstructora();
              }
            }}
            className="w-full rounded-xl border border-emerald-300/18 bg-[var(--sidebar-active)] px-4 py-3 text-sm text-slate-50 shadow-[0_10px_18px_rgba(0,0,0,0.18)] outline-none transition focus:border-emerald-300/60 focus:ring-4 focus:ring-emerald-400/10"
          >
            <option value="">Selecciona una empresa</option>
            {constructoras.map((constructora) => (
              <option key={constructora.constructora_id} value={constructora.constructora_id}>
                {constructora.nombre}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => onSetActiveView("constructoras", { openCreateConstructora: true })}
            className="w-full rounded-2xl border border-[var(--primary)]/35 bg-[linear-gradient(180deg,var(--primary),var(--primary-dark))] px-3 py-2 text-xs font-bold text-white shadow-[0_14px_28px_rgba(14,124,102,0.28)] transition hover:-translate-y-px hover:shadow-[0_16px_32px_rgba(14,124,102,0.34)] active:scale-[0.98]"
          >
            Nueva empresa
          </button>

          {selectedConstructora && (
            <button
              type="button"
              onClick={() => {
                setDeleteModalOpen(true);
                setDeleteConfirmText("");
                setDeleteError("");
              }}
              className="flex w-full items-center justify-center gap-2 rounded-2xl border border-red-300/25 bg-red-500/10 px-3 py-2 text-xs font-bold text-red-100 shadow-[0_10px_24px_rgba(185,28,28,0.08)] transition hover:-translate-y-px hover:border-red-300/45 hover:bg-red-500/18 active:scale-[0.98]"
            >
              <Trash2 size={15} />
              Eliminar empresa
            </button>
          )}

          {loadingConstructoras && (
            <p className="text-xs text-slate-500">Cargando empresas...</p>
          )}

          <div className="rounded-xl border border-emerald-300/15 bg-white/5 px-3 py-2 text-[11px] font-black uppercase tracking-wide text-emerald-100">
            Preset: {getPresetLabel(activePresetKey)}
          </div>
        </div>
      </section>

      <nav className="space-y-3">
        <p className="px-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Navegacion principal
        </p>
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.view;

          return (
            <button
              key={item.view}
              type="button"
              onClick={() => onSetActiveView(item.view)}
              disabled={item.disabled}
              className={`sidebar-nav-item flex w-full items-center gap-3 rounded-2xl border px-4 py-3 transition ${
                isActive
                  ? "sidebar-nav-item--active border-[var(--primary)]/35 bg-[var(--sidebar-active)] text-white"
                  : item.disabled
                    ? "cursor-not-allowed border-white/10 bg-white/5 text-slate-500"
                    : "border-transparent bg-transparent text-slate-300 hover:-translate-x-0.5 hover:border-white/10 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="group mt-10 rounded-2xl border border-white/10 bg-white/5 p-4 shadow-[0_12px_28px_rgba(15,23,42,0.16)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/20 hover:bg-white/7 hover:shadow-[0_18px_36px_rgba(15,23,42,0.22)]">
        <p className="text-xs text-slate-500 transition group-hover:text-emerald-200">
          Estado de la empresa
        </p>
        <div className="mt-3 space-y-2">
          {statusItems.map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between gap-4 rounded-xl px-2 py-1 text-sm transition group-hover:bg-white/5"
            >
              <span className="text-slate-400">{label}:</span>
              <span className="font-semibold text-slate-100">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="group mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 shadow-[0_12px_28px_rgba(15,23,42,0.16)] transition duration-300 hover:-translate-y-0.5 hover:border-emerald-200/20 hover:bg-white/7 hover:shadow-[0_18px_36px_rgba(15,23,42,0.22)]">
        <p className="text-xs text-slate-500 transition group-hover:text-emerald-200">Sesion activa</p>
        <p className="mt-2 text-sm font-semibold text-slate-100">
          {user?.nombre || user?.username || "Usuario"}
        </p>
        <button
          type="button"
          onClick={logout}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:-translate-y-px hover:border-red-300/30 hover:bg-red-500/10 hover:text-red-100 active:scale-[0.98]"
        >
          <LogOut size={16} />
          Cerrar sesion
        </button>
      </div>

      {deleteModal}
    </aside>
  );
}

export default Sidebar;
