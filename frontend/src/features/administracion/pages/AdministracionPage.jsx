import { useMemo, useState } from "react";
import { Building2, DatabaseZap, Settings, UsersRound } from "lucide-react";

import OrganizacionesView from "@/features/organizaciones/pages/OrganizacionesPage";
import ImportacionesView from "@/features/importaciones/pages/ImportacionesPage";
import ConfiguracionPage from "@/features/configuracion/pages/ConfiguracionPage";
import UsuariosPage from "@/features/usuarios/pages/UsuariosPage";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

const tabs = [
  { id: "empresas", label: "Empresas", icon: Building2, component: <OrganizacionesView /> },
  { id: "usuarios", label: "Usuarios", icon: UsersRound, component: <UsuariosPage /> },
  { id: "importaciones", label: "Importaciones", icon: DatabaseZap, component: <ImportacionesView /> },
  { id: "configuracion", label: "Configuración", icon: Settings, component: <ConfiguracionPage /> },
];

function AdministracionPage({ onSetActiveView, openCreateSignal }) {
  const { activeOrganizacion } = useOrganizacionActiva();
  const [activeTab, setActiveTab] = useState("empresas");
  const selectedTab = useMemo(() => tabs.find((tab) => tab.id === activeTab) || tabs[0], [activeTab]);

  const contentByTab = {
    empresas: <OrganizacionesView onSetActiveView={onSetActiveView} openCreateSignal={openCreateSignal} />,
    usuarios: <UsuariosPage />,
    importaciones: <ImportacionesView />,
    configuracion: <ConfiguracionPage />,
  };

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <section className="overflow-hidden rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,rgba(248,250,252,0.98),rgba(255,255,255,0.98))] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.08)] ring-1 ring-white/70">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.24em] text-slate-500">Administración</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
              Configuración de {activeOrganizacion?.nombre || "la plataforma"}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
              Agrupa empresas, usuarios, importaciones y configuración en un solo espacio administrativo para mantener el sidebar enfocado en gestión ambiental.
            </p>
          </div>

          <div className="grid grid-cols-4 gap-2 rounded-3xl border border-slate-200 bg-white p-3 text-slate-700 shadow-sm">
            <Building2 className="mx-auto" />
            <UsersRound className="mx-auto" />
            <DatabaseZap className="mx-auto" />
            <Settings className="mx-auto" />
          </div>
        </div>
      </section>

      <div className="overflow-x-auto rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-2 shadow-[var(--shadow-card)]">
        <div className="flex min-w-max gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = tab.id === selectedTab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-black transition ${isActive ? "bg-slate-900 text-white shadow-sm" : "text-[var(--text-muted)] hover:bg-slate-100 hover:text-slate-900"}`}
              >
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {contentByTab[selectedTab.id] || selectedTab.component}
    </main>
  );
}

export default AdministracionPage;
