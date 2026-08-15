import { useEffect, useMemo, useState } from "react";
import { Factory, FileSearch, Layers3, Plus, Settings2, Table2, Truck, Zap } from "lucide-react";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import ObrasView from "@/features/obras/pages/ObrasPage";
import RecepcionTrozasPage from "@/presets/aserradero/pages/RecepcionTrozasPage";
import ProduccionAserraderoPage from "@/presets/aserradero/pages/ProduccionAserraderoPage";
import SecadoAserraderoPage from "@/presets/aserradero/pages/SecadoAserraderoPage";
import EnergiaAserraderoPage from "@/presets/aserradero/pages/EnergiaAserraderoPage";
import TransporteForestalPage from "@/presets/aserradero/pages/TransporteForestalPage";
import ResiduosSubproductosPage from "@/presets/aserradero/pages/ResiduosSubproductosPage";
import LotesForestalesPage from "@/presets/aserradero/pages/LotesForestalesPage";
import { getEmpresaRegistrosAmbientales } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import ActivityCorePanel from "../components/ActivityCorePanel";
import TransportJourneyPanel from "../components/TransportJourneyPanel";
import MaterialsOperationalPanel from "../components/MaterialsOperationalPanel";

const tabBaseClass = "rounded-2xl px-4 py-3 text-sm font-black transition";
const STAGE_DONUT_SIZE = 220;
const STAGE_DONUT_CENTER = STAGE_DONUT_SIZE / 2;
const STAGE_DONUT_RADIUS = 78;
const STAGE_DONUT_CIRCUMFERENCE = 2 * Math.PI * STAGE_DONUT_RADIUS;
const STAGE_COLORS = ["#E11D48", "#EA580C", "#2563EB", "#7C3AED", "#059669", "#0891B2", "#84CC16", "#64748B"];

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
    { id: "materiales", label: "Materiales", scope: "materiales", component: <MaterialsOperationalPanel />, insight: "Materiales distingue adquisición, recepción, uso y destino con trazabilidad operacional." },
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

function normalizeRecord(row) {
  const metadata = row?.metadata && typeof row.metadata === "object" ? row.metadata : {};
  return {
    ...row,
    metadata,
    id: row?.id || row?.registro_id || `${row?.fecha || "sin-fecha"}-${row?.fuente_emision || row?.actividad || Math.random()}`,
    etapa: row?.etapa_nombre || row?.etapa || metadata.module || "Sin etapa",
    obra: row?.obra_nombre || row?.codigo_obra || row?.obra_codigo || metadata.lote || "Sin obra",
    fuente: row?.fuente_emision || row?.actividad || "Sin fuente",
    categoria: row?.categoria || row?.categoria_visible || metadata.aserradero_category || "Sin categoría",
    cantidad: row?.cantidad ?? row?.valor ?? row?.metadata?.cantidad ?? row?.metadata?.value ?? "—",
    unidad: row?.unidad || row?.metadata?.unit || "",
    fecha: row?.fecha || row?.created_at || row?.timestamp || "",
    emisiones: Number(row?.emisiones_kg_co2e ?? row?.emisiones ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0,
  };
}

function buildStages(records) {
  return Object.values(
    records.reduce((accumulator, record) => {
      const label = record.etapa || "Sin etapa";
      const current = accumulator[label] || { label, emissions: 0, records: 0 };
      current.emissions += Number(record.emisiones || 0);
      current.records += 1;
      accumulator[label] = current;
      return accumulator;
    }, {})
  ).sort((left, right) => right.emissions - left.emissions);
}

function StageDonut({ activeStage, stages, total, onSelect }) {
  return (
    <div className="relative h-[240px] w-[240px]">
      <svg viewBox={`0 0 ${STAGE_DONUT_SIZE} ${STAGE_DONUT_SIZE}`} className="h-full w-full overflow-visible" role="img" aria-label="Dona interactiva de emisiones por etapa">
        <circle cx={STAGE_DONUT_CENTER} cy={STAGE_DONUT_CENTER} r={STAGE_DONUT_RADIUS} fill="none" stroke="#E2E8F0" strokeWidth="28" />
        <g transform={`rotate(-90 ${STAGE_DONUT_CENTER} ${STAGE_DONUT_CENTER})`}>
          {stages.map((stage, index) => {
            const dash = Math.max((stage.share / 100) * STAGE_DONUT_CIRCUMFERENCE, 0.2);
            const offset = stages.slice(0, index).reduce(
              (sum, previous) => sum + Math.max((previous.share / 100) * STAGE_DONUT_CIRCUMFERENCE, 0.2),
              0
            );
            const isActive = activeStage?.label === stage.label;
            return (
              <circle
                key={stage.label}
                cx={STAGE_DONUT_CENTER}
                cy={STAGE_DONUT_CENTER}
                r={STAGE_DONUT_RADIUS}
                fill="none"
                stroke={stage.color}
                strokeDasharray={`${dash} ${STAGE_DONUT_CIRCUMFERENCE - dash}`}
                strokeDashoffset={-offset}
                strokeWidth={isActive ? 34 : 28}
                className="cursor-pointer transition-all duration-200"
                onClick={() => onSelect(stage)}
                onMouseEnter={() => onSelect(stage)}
              >
                <title>{`${stage.label}: ${formatNumber(stage.emissions, 1)} kg CO₂e · ${formatNumber(stage.share, 1)}%`}</title>
              </circle>
            );
          })}
        </g>
      </svg>

      <div className="pointer-events-none absolute inset-10 flex flex-col items-center justify-center rounded-full bg-white text-center shadow-[0_14px_35px_rgba(15,23,42,0.10)]">
        {activeStage ? (
          <>
            <p className="max-w-[130px] text-[10px] font-black uppercase leading-4 tracking-[0.16em] text-slate-500">{activeStage.label}</p>
            <p className="mt-1 text-xl font-black leading-tight text-[var(--text-main)]">{formatNumber(activeStage.emissions, 1)}</p>
            <p className="text-xs font-black text-slate-500">kg CO₂e · {formatNumber(activeStage.share, 1)}%</p>
          </>
        ) : (
          <>
            <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-500">Total etapas</p>
            <p className="mt-1 text-2xl font-black text-[var(--text-main)]">{formatNumber(total, 1)}</p>
            <p className="text-xs font-black text-slate-500">kg CO₂e</p>
          </>
        )}
      </div>
    </div>
  );
}

function StagesInsideWorksPanel({ organizacionId }) {
  const [records, setRecords] = useState([]);
  const [selectedStage, setSelectedStage] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRecords() {
      if (!organizacionId) {
        setRecords([]);
        setSelectedStage(null);
        return;
      }
      try {
        setLoading(true);
        const response = await getEmpresaRegistrosAmbientales(organizacionId);
        const rows = Array.isArray(response) ? response : response?.results || response?.data || response?.registros || [];
        if (!cancelled) {
          setRecords(rows.map(normalizeRecord));
          setSelectedStage(null);
        }
      } catch {
        if (!cancelled) {
          setRecords([]);
          setSelectedStage(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadRecords();
    return () => {
      cancelled = true;
    };
  }, [organizacionId]);

  const total = records.reduce((sum, record) => sum + Number(record.emisiones || 0), 0);
  const stages = buildStages(records).map((stage, index) => ({
    ...stage,
    color: STAGE_COLORS[index % STAGE_COLORS.length],
    share: total > 0 ? (stage.emissions / total) * 100 : 0,
  }));
  const selectedRecords = selectedStage
    ? records
        .filter((record) => record.etapa === selectedStage.label)
        .sort((left, right) => new Date(right.fecha || 0) - new Date(left.fecha || 0))
        .slice(0, 8)
    : [];

  return (
    <section className="rounded-[32px] border border-[var(--border)] bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96))] p-6 shadow-[var(--shadow-card)] ring-1 ring-white/70">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-700">Etapas dentro de obras</p>
          <h3 className="mt-1 text-2xl font-black text-[var(--text-main)]">Participación de emisiones por etapa</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
            Selecciona una etapa en la dona para revisar sus últimos registros. Las etapas viven dentro de Obras porque explican dónde se acumula la huella de cada proyecto.
          </p>
        </div>
        <span className="w-fit rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-xs font-black text-emerald-800">
          {loading ? "Cargando" : `${formatNumber(stages.length, 0)} etapas`}
        </span>
      </div>

      {stages.length ? (
        <div className="mt-6 grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)] xl:items-start">
          <div className="flex flex-col items-center gap-4">
            <StageDonut activeStage={selectedStage} stages={stages} total={total} onSelect={setSelectedStage} />
            <button
              type="button"
              onClick={() => setSelectedStage(null)}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-xs font-black text-slate-600 transition hover:bg-slate-50"
            >
              Limpiar selección
            </button>
          </div>

          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {stages.map((stage) => {
                const active = selectedStage?.label === stage.label;
                return (
                  <button
                    key={stage.label}
                    type="button"
                    onClick={() => setSelectedStage(stage)}
                    className={`rounded-2xl border bg-white p-4 text-left shadow-sm transition ${active ? "border-emerald-300 ring-4 ring-emerald-100" : "border-slate-200 hover:border-emerald-200"}`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="mt-1 h-3 w-3 rounded-full" style={{ backgroundColor: stage.color }} />
                      <div>
                        <p className="font-black text-[var(--text-main)]">{stage.label}</p>
                        <p className="mt-1 text-xs font-bold text-slate-500">{formatNumber(stage.records, 0)} registros · {formatNumber(stage.share, 1)}%</p>
                        <p className="mt-2 text-sm font-black text-sky-950">{formatNumber(stage.emissions, 1)} kg CO₂e</p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            <StageRecordsTable records={selectedRecords} selectedStage={selectedStage} />
          </div>
        </div>
      ) : (
        <StageEmptyState title="Aún no hay etapas con emisiones" description="Cuando la obra tenga registros asociados a etapas, Carbono Zero mostrará la dona y los últimos movimientos de cada etapa." />
      )}
    </section>
  );
}

function StageRecordsTable({ records, selectedStage }) {
  if (!selectedStage) {
    return (
      <StageEmptyState
        title="Selecciona una etapa para ver sus registros"
        description="La tabla quedará preparada y mostrará fecha, obra, fuente, categoría, cantidad y kg CO₂e de los últimos registros asociados a la etapa seleccionada."
      />
    );
  }

  if (!records.length) {
    return (
      <StageEmptyState
        title={`Sin registros recientes en ${selectedStage.label}`}
        description="La etapa existe en la lectura general, pero no hay registros recientes disponibles para mostrar en esta tabla."
      />
    );
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Últimos registros</p>
          <h4 className="text-xl font-black text-[var(--text-main)]">{selectedStage.label}</h4>
        </div>
        <Table2 className="text-emerald-700" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-3 text-left">Fecha</th>
              <th className="px-3 py-3 text-left">Obra</th>
              <th className="px-3 py-3 text-left">Fuente</th>
              <th className="px-3 py-3 text-left">Categoría</th>
              <th className="px-3 py-3 text-right">Cantidad</th>
              <th className="px-3 py-3 text-right">Emisiones</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id} className="border-b border-slate-100 last:border-0">
                <td className="px-3 py-3 font-semibold text-slate-600">{record.fecha ? String(record.fecha).slice(0, 10) : "—"}</td>
                <td className="px-3 py-3 font-black text-[var(--text-main)]">{record.obra}</td>
                <td className="px-3 py-3 text-slate-700">{record.fuente}</td>
                <td className="px-3 py-3 text-slate-700">{record.categoria}</td>
                <td className="px-3 py-3 text-right font-semibold text-slate-700">{record.cantidad} {record.unidad}</td>
                <td className="px-3 py-3 text-right font-black text-sky-950">{formatNumber(record.emisiones, 1)} kg CO₂e</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function StageEmptyState({ description, title }) {
  return (
    <section className="rounded-3xl border border-dashed border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.72),rgba(255,255,255,0.92))] p-6 text-center shadow-sm">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-200 bg-white text-emerald-700 shadow-sm">
        <FileSearch size={24} />
      </div>
      <h4 className="mt-4 text-xl font-black text-[var(--text-main)]">{title}</h4>
      <p className="mx-auto mt-2 max-w-2xl text-sm font-semibold leading-6 text-[var(--text-muted)]">{description}</p>
    </section>
  );
}

function OperacionPage() {
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const presetKey = activeOrganizacion?.preset || "construccion";
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
              Procesos de {activeOrganizacion?.nombre || "la empresa"}
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

      <ActivityCorePanel organizacionId={activeOrganizacionId} />
      <TransportJourneyPanel organizacionId={activeOrganizacionId} />

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
        <div className="space-y-6">
          <div className={selectedTab.id === "unidades" ? "[&>div]:!space-y-0 [&>div]:flex [&>div]:flex-col [&>div]:gap-6 [&>div>header]:hidden [&>div>section:first-of-type]:hidden [&>div>section:nth-of-type(2)]:order-2 [&>div>section:nth-of-type(3)]:order-1 [&>div>div.space-y-6]:order-1" : ""}>
            {selectedTab.id === "materiales" ? <MaterialsOperationalPanel organizacionId={activeOrganizacionId} /> : selectedTab.component}
          </div>
          {selectedTab.id === "unidades" ? <StagesInsideWorksPanel organizacionId={activeOrganizacionId} /> : null}
        </div>
      ) : (
        <OperationPlaceholder tab={selectedTab} />
      )}
    </main>
  );
}

export default OperacionPage;
