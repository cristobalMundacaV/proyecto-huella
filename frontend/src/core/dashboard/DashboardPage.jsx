import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BarChart3, Database, Factory, Leaf, Radar } from "lucide-react";

import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
import ExecutiveSummary from "@/features/dashboard/components/ExecutiveSummary";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { getEnvironmentalKpis } from "@/features/environmental/services/environmentalKpiApi";
import KpiCard from "@/shared/components/KpiCard";
import PlatformLoader from "@/shared/components/PlatformLoader";
import {
  getConstructoraDashboard,
  getConstructoraEmisiones,
  getConstructoraEstado,
  getEmpresaRegistrosAmbientales,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";

const DASHBOARD_REFRESH_INTERVAL_MS = 12000;

const PARTICIPATION_COLORS = ["#E11D48", "#EA580C", "#2563EB", "#7C3AED", "#059669", "#0891B2", "#84CC16", "#64748B"];

const normalizeRows = (input) => {
  const rows = Array.isArray(input)
    ? input
    : input?.results || input?.data || input?.datos || input?.registros || input?.registros_emision || [];

  return rows.map((row) => ({
    ...row,
    metadata: row?.metadata && typeof row.metadata === "object" ? row.metadata : {},
    emisiones: Number(row?.emisiones ?? row?.emisiones_kg_co2e ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0,
    categoria_visible: row?.categoria || row?.categoria_visible || row?.metadata?.aserradero_category || "Otros",
    etapa_visible: row?.etapa_nombre || row?.etapa || row?.metadata?.module || "Sin etapa",
    obra_visible: row?.obra_nombre || row?.codigo_obra || row?.obra_codigo || row?.metadata?.lote || "Sin unidad",
    fuente_visible: row?.fuente_emision || row?.actividad || "Sin fuente",
  }));
};

function groupBy(rows, key, outputKey = "name") {
  return Object.values(
    rows.reduce((accumulator, row) => {
      const label = row[key] || "Sin datos";
      const current = accumulator[label] || { [outputKey]: label, emisiones: 0, registros: 0 };
      current.emisiones += Number(row.emisiones || 0);
      current.registros += 1;
      accumulator[label] = current;
      return accumulator;
    }, {})
  ).sort((left, right) => right.emisiones - left.emisiones);
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function getRowQuantity(row) {
  const candidates = [
    row?.cantidad,
    row?.valor,
    row?.quantity,
    row?.litros,
    row?.metadata?.cantidad,
    row?.metadata?.valor,
    row?.metadata?.value,
    row?.metadata?.litros,
    row?.metadata?.liters,
    row?.metadata?.reading,
  ];
  const found = candidates.find((value) => Number.isFinite(Number(value)) && Number(value) > 0);
  return Number(found || 0);
}

function calculateDieselLiters(rows) {
  return rows.reduce((total, row) => {
    const text = normalizeText(`${row?.fuente_visible} ${row?.categoria_visible} ${row?.unidad} ${row?.tipo} ${row?.metadata?.unit} ${row?.metadata?.tipo}`);
    const isDiesel = /diesel|petroleo|combustible/.test(text);
    const isLiters = /litro|litros|liter|liters|\bl\b/.test(text) || isDiesel;
    if (!isDiesel || !isLiters) return total;
    return total + getRowQuantity(row);
  }, 0);
}

function getKpiCardValue(kpis, id) {
  const card = (kpis?.cards || []).find((item) => item.id === id);
  const value = Number(card?.value);
  return Number.isFinite(value) && value > 0 ? value : null;
}

function buildExecutiveScenario({ activePresetKey, byCategory, bySource, byStage, footprintPerM2, rows, totalEmissions }) {
  const total = Number(totalEmissions || 0);
  const dominantSource = bySource[0];
  const dominantStage = byStage[0];
  const dominantCategory = byCategory[0];
  const sourceConcentration = total > 0 && dominantSource?.emisiones ? (dominantSource.emisiones / total) * 100 : 0;
  const stageConcentration = total > 0 && dominantStage?.emisiones ? (dominantStage.emisiones / total) * 100 : 0;
  const dieselLiters = calculateDieselLiters(rows);
  const dieselPresent = dieselLiters > 0 || rows.some((row) => /diesel|combustible|petroleo/.test(normalizeText(`${row.fuente_visible} ${row.categoria_visible}`)));
  const totalEmissionLevel = total > 100000 ? "Alto" : total > 10000 ? "Medio" : total > 0 ? "Bajo" : "Sin datos";
  const potentialReduction = sourceConcentration > 0 ? Math.min(35, Math.max(3, sourceConcentration * 0.15)) : 0;
  const riskScore = Math.min(
    100,
    Math.round(
      sourceConcentration * 0.55 +
        stageConcentration * 0.25 +
        (total > 100000 ? 20 : total > 10000 ? 12 : total > 0 ? 5 : 0) +
        (dieselPresent ? 8 : 0)
    )
  );
  const isConstruction = activePresetKey === "construccion";
  const sourceLabel = dominantSource?.fuente || "Sin fuente suficiente";
  const stageLabel = dominantStage?.etapa || "Sin etapa suficiente";
  const categoryLabel = dominantCategory?.categoria || "Sin categoria suficiente";

  const riskProfile = {
    score: riskScore,
    label: riskScore > 70 ? "Alto" : riskScore > 30 ? "Medio" : "Bajo",
    factors: {
      dieselPresent,
      dieselLiters,
      footprintPerM2,
      dominantStageLabel: stageLabel,
      stageConcentration,
      totalEmissions: { label: totalEmissionLevel },
      dominantSourceLabel: sourceLabel,
      dominantSourcePercentage: sourceConcentration,
      sourceConcentration,
      potentialReduction,
    },
  };

  if (!total || !dominantSource?.emisiones || !potentialReduction) {
    return { optimizedScenario: null, riskProfile };
  }

  const optimizedScenario = {
    currentTotal: total,
    simulatedTotal: Math.max(total * (1 - potentialReduction / 100), 0),
    reductionPct: potentialReduction,
    targetSource: sourceLabel,
    targetCategory: categoryLabel,
    targetStage: stageLabel,
    activityReduction: Math.min(45, Math.max(10, potentialReduction * 2.4)),
    dieselReduction: dieselPresent ? Math.min(20, Math.max(5, potentialReduction)) : 0,
    recommendedActions: isConstruction
      ? [
          `Validar respaldo técnico y cantidades asociadas a ${sourceLabel}.`,
          `Comparar factor de emisión, ficha técnica/EPD y proveedor antes de repetir compras en ${stageLabel}.`,
          "Revisar si la presión viene de cantidad, especificación o clasificación del registro antes de comprometer cambios de diseño o abastecimiento.",
        ]
      : [
          `Validar respaldo técnico y cantidades asociadas a ${sourceLabel}.`,
          `Comparar factor aplicado, proveedor y evidencia operacional antes de escalar cambios en ${stageLabel}.`,
          "Separar si la presión viene de consumo real, proceso, proveedor o clasificación del registro.",
        ],
    evidenceNeeded: isConstruction
      ? ["guia de despacho", "factura", "ficha tecnica", "respaldo de cantidad"]
      : ["documento de respaldo", "registro operacional", "factor aplicado"],
    operationalNextStep: `Revisar datos, evidencia y responsable operativo para ${sourceLabel} en ${stageLabel}.`,
  };

  return { optimizedScenario, riskProfile };
}

function getConicGradient(items) {
  let current = 0;
  const parts = items.map((item) => {
    const start = current;
    const end = current + Number(item.share || 0);
    current = end;
    return `${item.color} ${start}% ${end}%`;
  });
  return parts.length ? `conic-gradient(${parts.join(", ")})` : "conic-gradient(#CBD5E1 0% 100%)";
}

function EmissionParticipationPanel({ data, description, nameKey, title, totalLabel = "Total obra" }) {
  const total = data.reduce((sum, item) => sum + Number(item.emisiones || 0), 0);
  const items = data.map((item, index) => {
    const share = total > 0 ? (Number(item.emisiones || 0) / total) * 100 : 0;
    return {
      ...item,
      color: PARTICIPATION_COLORS[index % PARTICIPATION_COLORS.length],
      label: item[nameKey] || "Sin datos",
      share,
    };
  });
  const dominant = items[0];

  return (
    <section className="overflow-hidden rounded-[32px] border border-[var(--border)] bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96))] p-6 shadow-[var(--shadow-card)] ring-1 ring-white/70">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-700">Lectura visual</p>
          <h3 className="mt-1 text-2xl font-black text-[var(--text-main)]">{title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">{description}</p>
        </div>
        {dominant ? (
          <span className="w-fit rounded-2xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-black text-rose-700">
            Dominante: {dominant.label}
          </span>
        ) : null}
      </div>

      {items.length ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-center">
          <div className="flex justify-center">
            <div className="relative h-52 w-52 rounded-full shadow-[inset_0_0_0_1px_rgba(15,23,42,0.08)]" style={{ background: getConicGradient(items) }}>
              <div className="absolute inset-10 flex flex-col items-center justify-center rounded-full bg-white text-center shadow-[0_14px_35px_rgba(15,23,42,0.10)]">
                <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-500">{totalLabel}</p>
                <p className="mt-1 text-2xl font-black text-[var(--text-main)]">{formatNumber(total, 1)}</p>
                <p className="text-xs font-black text-slate-500">kg CO₂e</p>
              </div>
            </div>
          </div>

          <div className="max-h-[390px] space-y-3 overflow-y-auto pr-2 scroll-smooth">
            {items.map((item) => (
              <article key={`${title}-${item.label}`} className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-3">
                    <span className="mt-1 h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
                    <div>
                      <p className="text-base font-black text-[var(--text-main)]">{item.label}</p>
                      <p className="text-xs font-bold text-slate-500">{item.registros} registros asociados</p>
                    </div>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="text-base font-black text-sky-950">{formatNumber(item.emisiones, 1)} kg CO₂e</p>
                    <p className="text-xs font-black text-slate-500">{formatNumber(item.share, 1)}%</p>
                  </div>
                </div>
                <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200">
                  <div className="h-full rounded-full" style={{ width: `${Math.min(100, Math.max(1, item.share))}%`, backgroundColor: item.color }} />
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <div className="mt-6 flex min-h-[220px] items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-white/70 text-sm font-semibold text-[var(--text-muted)]">
          Sin datos suficientes para construir esta lectura.
        </div>
      )}
    </section>
  );
}

function DashboardPage({ onStatusChange }) {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);
  const [data, setData] = useState(null);
  const [ambientRecords, setAmbientRecords] = useState([]);
  const [emissionKpis, setEmissionKpis] = useState(null);
  const [environmentalKpis, setEnvironmentalKpis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refreshDashboard = useCallback(async (showLoading = false) => {
    if (!activeConstructoraId) {
      setData(null);
      setAmbientRecords([]);
      setEmissionKpis(null);
      setEnvironmentalKpis(null);
      onStatusChange?.(null);
      setLoading(false);
      return;
    }

    if (showLoading) setLoading(true);
    setError("");

    const [dashboardResult, estadoResult, emissionsResult, recordsResult, environmentalKpiResult] = await Promise.allSettled([
      getConstructoraDashboard(activeConstructoraId, { light: "1" }),
      getConstructoraEstado(activeConstructoraId),
      getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
      getEmpresaRegistrosAmbientales(activeConstructoraId),
      getEnvironmentalKpis(activeConstructoraId),
    ]);

    const normalizedRecords = recordsResult.status === "fulfilled" ? normalizeRows(recordsResult.value) : [];

    if (dashboardResult.status === "fulfilled") setData(dashboardResult.value);
    if (emissionsResult.status === "fulfilled") setEmissionKpis(emissionsResult.value?.kpis || null);
    if (environmentalKpiResult.status === "fulfilled") setEnvironmentalKpis(environmentalKpiResult.value || null);
    if (recordsResult.status === "fulfilled") setAmbientRecords(normalizedRecords);

    if (estadoResult.status === "fulfilled") {
      onStatusChange?.({
        ...estadoResult.value,
        registros_emision: normalizedRecords.length || estadoResult.value?.registros_emision || 0,
      });
    } else if (normalizedRecords.length) {
      onStatusChange?.({ registros_emision: normalizedRecords.length });
    }

    if (dashboardResult.status === "rejected" && recordsResult.status === "rejected") {
      throw dashboardResult.reason || recordsResult.reason;
    }

    if (showLoading) setLoading(false);
  }, [activeConstructoraId, onStatusChange]);

  useEffect(() => {
    let cancelled = false;
    let intervalId;

    async function load() {
      try {
        await refreshDashboard(true);
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.response?.data?.error || "No se pudo cargar el tablero de la empresa.");
          setLoading(false);
        }
      }

      intervalId = window.setInterval(() => {
        refreshDashboard(false).catch(() => undefined);
      }, DASHBOARD_REFRESH_INTERVAL_MS);
    }

    load();

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [refreshDashboard]);

  const rows = useMemo(() => {
    const dashboardRows = normalizeRows(data?.datos || []);
    const scopedRows = activePreset.key === DEFAULT_PRESET_KEY
      ? dashboardRows
      : ambientRecords.filter((row) => row.metadata?.preset === activePreset.key || !row.metadata?.preset);
    return scopedRows.length ? scopedRows : dashboardRows;
  }, [activePreset.key, ambientRecords, data]);

  const totalEmissions = Number(emissionKpis?.emisiones_totales ?? data?.total_emisiones ?? rows.reduce((sum, row) => sum + row.emisiones, 0));
  const byCategory = useMemo(() => groupBy(rows, "categoria_visible", "categoria"), [rows]);
  const byStage = useMemo(() => groupBy(rows, "etapa_visible", "etapa"), [rows]);
  const bySource = useMemo(() => groupBy(rows, "fuente_visible", "fuente"), [rows]);
  const byUnit = useMemo(() => groupBy(rows, "obra_visible", "unidad"), [rows]);

  const criticalCategory = byCategory[0]?.categoria || data?.categoria_critica || "Sin datos";
  const criticalStage = byStage[0]?.etapa || data?.etapa_critica || data?.unidad_critica || "Sin datos";
  const criticalSource = bySource[0]?.fuente || data?.fuente_critica || "Sin datos";
  const criticalUnit = byUnit[0]?.unidad || data?.obra_critica || "Sin datos";
  const topShare = totalEmissions > 0 && bySource[0]?.emisiones ? (bySource[0].emisiones / totalEmissions) * 100 : 0;
  const footprintPerM2 = getKpiCardValue(environmentalKpis, "huella_m2");
  const { optimizedScenario, riskProfile } = useMemo(
    () => buildExecutiveScenario({ activePresetKey: activePreset.key, byCategory, bySource, byStage, footprintPerM2, rows, totalEmissions }),
    [activePreset.key, byCategory, bySource, byStage, footprintPerM2, rows, totalEmissions]
  );

  if (loading && !data && !ambientRecords.length) {
    return <PlatformLoader title="Cargando tablero de empresa" description="Estamos preparando indicadores, focos críticos y recomendaciones ambientales." />;
  }

  if (error && !rows.length) {
    return <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm font-semibold text-rose-800">{error}</div>;
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <section className="overflow-hidden rounded-[32px] border border-emerald-300/40 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.18),transparent_32%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] p-6 shadow-[0_28px_80px_rgba(15,118,110,0.14)] ring-1 ring-white/70">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-emerald-800 shadow-sm"><Leaf size={28} /></div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-700">Dashboard ambiental</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">Carbono Zero</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">Convierte datos reales de {activePreset.unitPluralLabel.toLowerCase()} en medición, trazabilidad y decisiones para reducir emisiones durante la operación.</p>
            </div>
          </div>

          <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-sm shadow-sm">
            <p className="font-black text-emerald-900">Recomendación principal</p>
            <p className="mt-1 max-w-sm leading-6 text-slate-600">Prioriza {criticalSource} en {criticalStage}. Es el foco más relevante para transformar la medición en acción ambiental.</p>
          </div>
        </div>
      </section>

      <ExecutiveSummary fuenteCritica={criticalSource} unidadCritica={criticalStage} optimizedScenario={optimizedScenario} riskProfile={riskProfile} />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KpiCard icon={<Activity />} title="Emisiones totales" value={`${formatNumber(totalEmissions, 1)} kg CO₂e`} />
        <KpiCard icon={<Factory />} title={`${activePreset.unitLabel} crítica`} value={criticalUnit} />
        <KpiCard icon={<AlertTriangle />} title="Categoría crítica" value={criticalCategory} />
        <KpiCard icon={<Database />} title="Fuente crítica" value={criticalSource} />
        <KpiCard icon={<Radar />} title="Concentración principal" value={`${formatNumber(topShare, 1)}%`} />
        <KpiCard icon={<BarChart3 />} title="Registros analizados" value={formatNumber(rows.length, 0)} />
      </section>

      <section className="space-y-6">
        <EmissionParticipationPanel
          data={byUnit}
          description="Compara qué obra o unidad concentra más emisiones dentro de la empresa. Sirve para detectar dónde mirar primero antes de abrir detalle por etapa o fuente."
          nameKey="unidad"
          title="Participación de emisiones por obra"
        />
        <EmissionParticipationPanel
          data={byStage}
          description="Muestra qué etapa de obra concentra la mayor responsabilidad dentro de la huella. Mientras más grande el segmento, mayor prioridad operativa."
          nameKey="etapa"
          title="Participación de emisiones por etapa"
        />
        <EmissionParticipationPanel
          data={byCategory}
          description="Agrupa las emisiones por categoría ambiental para distinguir si la presión viene de materiales, energía, maquinaria, residuos o transporte."
          nameKey="categoria"
          title="Participación de emisiones por categoría"
        />
        <EmissionParticipationPanel
          data={bySource}
          description="Muestra todas las fuentes que generan emisiones. Mientras más grande sea el segmento, mayor es la responsabilidad de esa fuente dentro de la huella de la obra."
          nameKey="fuente"
          title="Participación de emisiones por fuente"
        />
      </section>

      <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />
    </main>
  );
}

export default DashboardPage;
