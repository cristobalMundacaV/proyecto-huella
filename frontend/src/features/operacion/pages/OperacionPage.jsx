import { useMemo, useState } from "react";
import { Factory, Layers3, Plus, Route, Settings2, Truck, Zap } from "lucide-react";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import ObrasView from "@/features/obras/pages/ObrasPage";
import EtapasObraView from "@/features/etapas/pages/EtapasPage";
import RecepcionTrozasPage from "@/presets/aserradero/pages/RecepcionTrozasPage";
import ProduccionAserraderoPage from "@/presets/aserradero/pages/ProduccionAserraderoPage";
import SecadoAserraderoPage from "@/presets/aserradero/pages/SecadoAserraderoPage";
import EnergiaAserraderoPage from "@/presets/aserradero/pages/EnergiaAserraderoPage";
import TransporteForestalPage from "@/presets/aserradero/pages/TransporteForestalPage";
import ResiduosSubproductosPage from "@/presets/aserradero/pages/ResiduosSubproductosPage";
import LotesForestalesPage from "@/presets/aserradero/pages/LotesForestalesPage";

const tabBaseClass = "rounded-2xl px-4 py-3 text-sm font-black transition";

function getTabsForPreset(presetKey) {
  if (presetKey === "aserradero") {
    return [
      { id: "recepcion", label: "Recepción", scope: "dashboard", component: <RecepcionTrozasPage />, insight: "Controla entrada de trozas, lote, volumen y trazabilidad desde el origen." },
      { id: "produccion", label: "Producción", scope: "materiales", component: <ProduccionAserraderoPage />, insight: "Mide rendimiento de aserrío y vincula producción con consumo energético y residuos." },
      { id: "secado", label: "Secado", scope: "energia", component: <SecadoAserraderoPage />, insight: "Prioriza cámara, humedad y energía para reducir emisiones por etapa de secado." },
      { id: "energia", label: "Energía", scope: "energia", component: <EnergiaAserraderoPage />, insight: "Separa electricidad, biomasa, generadores y consumo térmico para detectar desvíos." },
      { id: "transporte", label: "Transporte", scope: "transporte", component: <TransporteForestalPage />, insight: "Evalúa rutas, origen, destino, distancia y carga para estimar huella logística." },
      { id: "lotes", label: "Lotes", scope: "obra", component: <LotesForestalesPage />, insight: "Los lotes deben volver a conectar recepción, transporte, procesos y emisiones específicas." },
      { id: "residuos", label: "Residuos", scope: "evidencias", component: <ResiduosSubproductosPage />, insight: "Diferencia residuos, subproductos y valorización para no castigar material aprovechable." },
    ];
  }

  if (presetKey === "transporte") {
    return [
      { id: "flota", label: "Flota", scope: "maquinaria", placeholder: "Administra vehículos, capacidad, estado operativo y emisiones por unidad.", insight: "La flota debe conectar combustible, kilometraje, mantención y carga para medir eficiencia real." },
      { id: "viajes", label: "Viajes", scope: "transporte", placeholder: "Centraliza viajes, origen, destino, carga y emisiones por ruta.", insight: "Cada viaje debe transformarse en huella por ruta, vehículo y tonelada transportada." },
      { id: "combustible", label: "Combustible", scope: "iot", placeholder: "Controla cargas, rendimiento, consumo y telemetría de combustible.", insight: "El combustible es el dato operacional más directo para detectar desvíos y consumos anómalos." },
      { id: "rutas", label: "Rutas", scope: "transporte", placeholder: "Evalúa rutas frecuentes, kilómetros críticos y oportunidades de optimización.", insight: "La distancia debe pasar de dato logístico a variable ambiental prioritaria." },
      { id: "mantencion", label: "Mantenciones", scope: "maquinaria", placeholder: "Relaciona mantenimiento, disponibilidad y eficiencia ambiental de la flota.", insight: "Mantención deficiente aumenta consumo, ralentí y emisiones por kilómetro." },
    ];
  }

  return [
    { id: "unidades", label: presetKey === "industrial" ? "Líneas" : "Obras", scope: "obra", component: <ObrasView />, insight: "Cada obra debe mostrar qué etapa, fuente y actividad explican la huella acumulada." },
    { id: "etapas", label: presetKey === "industrial" ? "Procesos" : "Etapas", scope: "etapas", component: <EtapasObraView />, insight: "Las etapas permiten priorizar dónde intervenir primero sin mirar registros aislados." },
    { id: "materiales", label: "Materiales", scope: "materiales", placeholder: "Analiza materiales críticos, proveedores y partidas con mayor carbono incorporado.", insight: "Materiales debe responder qué compra o partida concentra carbono incorporado." },
    { id: "maquinaria", label: "Maquinaria", scope: "maquinaria", placeholder: "Controla combustible, horas de uso, ralentí, mantención y desempeño por equipo.", insight: "Maquinaria debe cruzar consumo, horas encendido y avance para detectar ineficiencia." },
    { id: "transporte", label: "Transporte", scope: "transporte", placeholder: "Evalúa viajes, proveedores cercanos, kilómetros y logística asociada a la obra.", insight: "Transporte debe estimar huella por ruta y proponer consolidación de viajes." },
    { id: "energia", label: "Energía", scope: "energia", placeholder: "Revisa kWh, generadores, horarios de consumo y desviaciones por etapa.", insight: "Energía debe separar consumo por etapa para detectar generadores o horarios críticos." },
    { id: "residuos", label: "Residuos", scope: "evidencias", placeholder: "Gestiona segregación, valorización, retiros trazables y disposición final.", insight: "Residuos debe diferenciar disposición final de valorización para mejorar gestión circular." },
  ];
}

function OperationPlaceholder({ tab }) {
  return (
    <section className="rounded-[32px] border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow-card)] ring-1 ring-white/70">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-700">Proceso operacional</p>
          <h3 className="mt-2 text-2xl font-black text-[var(--text-main)]">{tab.label}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">{tab.placeholder}</p>
        </div>
        <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800">
          <Settings2 size={28} />
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-dashed border-emerald-200 bg-emerald-50/50 p-5 text-sm leading-6 text-emerald-900">
        Esta sección queda concentrada dentro de Operación para evitar saturar el sidebar. En la siguiente fase se reemplazará por tablas, gráficos y acciones en modal según el proceso.
      </div>
    </section>
  );
}

function triggerHiddenCreateObraButton() {
  const button = document.querySelector('[data-create-obra-button="true"]');
  if (button) button.click();
}

function OperacionPage() {
  const { activeConstructora } = useConstructoraActiva();
  const presetKey = activeConstructora?.preset || "construccion";
  const tabs = useMemo(() => getTabsForPreset(presetKey), [presetKey]);
  const [activeTab, setActiveTab] = useState(tabs[0]?.id || "unidades");
  const selectedTab = tabs.find((tab) => tab.id === activeTab) || tabs[0];
  const showNewObraButton = selectedTab?.id === "unidades" && presetKey !== "industrial";

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <section className="overflow-hidden rounded-[32px] border border-emerald-300/40 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.20),transparent_32%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] p-6 shadow-[0_28px_80px_rgba(15,118,110,0.14)] ring-1 ring-white/70">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-700">Operación ambiental</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
              Procesos de {activeConstructora?.nombre || "la empresa"}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
              Centraliza obras, etapas y procesos operacionales en una sola vista.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {showNewObraButton ? (
              <button
                type="button"
                onClick={triggerHiddenCreateObraButton}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-5 py-3 text-sm font-black text-emerald-800 shadow-sm transition hover:bg-emerald-50"
              >
                <Plus size={17} />
                Nueva obra
              </button>
            ) : null}
            <div className="grid grid-cols-3 gap-2 rounded-3xl border border-white/70 bg-white/70 p-3 text-center shadow-sm">
              <Factory className="mx-auto text-emerald-700" />
              <Truck className="mx-auto text-emerald-700" />
              <Zap className="mx-auto text-emerald-700" />
            </div>
          </div>
        </div>
      </section>

      <div className="overflow-x-auto rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-2 shadow-[var(--shadow-card)]">
        <div className="flex min-w-max gap-2">
          {tabs.map((tab) => {
            const isActive = tab.id === selectedTab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`${tabBaseClass} ${isActive ? "bg-emerald-700 text-white shadow-sm" : "bg-transparent text-[var(--text-muted)] hover:bg-emerald-50 hover:text-emerald-800"}`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {selectedTab.component ? (
        <div className={selectedTab.id === "unidades" ? "[&>div>header]:hidden [&>div>section:first-of-type]:hidden" : ""}>
          {selectedTab.component}
        </div>
      ) : (
        <OperationPlaceholder tab={selectedTab} />
      )}
    </main>
  );
}

export default OperacionPage;
