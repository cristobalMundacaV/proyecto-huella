import { BarChart3 } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";

const numberFrom = (record, field, fallback = 0) =>
  Number(record?.metadata?.[field] ?? record?.[field] ?? fallback) || 0;

const uniqueCount = (records, field) =>
  new Set(records.map((record) => record?.metadata?.[field]).filter(Boolean)).size;

const noFactorCount = (records) =>
  records.filter((record) => !Number(record?.factor_emision || 0)).length;

const sumField = (records, field, fallbackField = null) =>
  records.reduce((total, record) => total + numberFrom(record, field, fallbackField ? record?.[fallbackField] : 0), 0);

const averageField = (records, field) => {
  const values = records.map((record) => numberFrom(record, field, null)).filter((value) => value > 0);
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
};

function getKpis(moduleKey, records) {
  const emissions = records.reduce(
    (total, record) => total + Number(record?.emisiones_kg_co2e ?? record?.emisiones ?? 0),
    0
  );

  const definitions = {
    recepcion_trozas: [
      { label: "m3 recibidos", value: formatNumber(sumField(records, "volumen_m3", "cantidad"), 1) },
      { label: "Lotes registrados", value: formatNumber(uniqueCount(records, "lote"), 0) },
      { label: "Proveedores", value: formatNumber(uniqueCount(records, "proveedor_madera"), 0) },
      { label: "Registros sin factor", value: formatNumber(noFactorCount(records), 0), tone: "amber" },
    ],
    produccion: [
      { label: "m3 procesados", value: formatNumber(sumField(records, "volumen_entrada_m3", "cantidad"), 1) },
      { label: "Rendimiento promedio", value: `${formatNumber(averageField(records, "rendimiento_pct"), 1)}%` },
      { label: "Lotes procesados", value: formatNumber(uniqueCount(records, "lote"), 0) },
      { label: "Registros sin factor", value: formatNumber(noFactorCount(records), 0), tone: "amber" },
    ],
    secado: [
      { label: "m3 secados", value: formatNumber(sumField(records, "volumen_secado_m3"), 1) },
      { label: "kWh registrados", value: formatNumber(sumField(records, "energia_kwh", "cantidad"), 1) },
      { label: "Horas de secado", value: formatNumber(sumField(records, "horas_secado"), 1) },
      { label: "Humedad final promedio", value: `${formatNumber(averageField(records, "humedad_final_pct"), 1)}%` },
    ],
    energia: [
      { label: "kWh totales", value: formatNumber(sumField(records, "consumo_kwh", "cantidad"), 1) },
      { label: "Areas registradas", value: formatNumber(uniqueCount(records, "area"), 0) },
      { label: "Turnos registrados", value: formatNumber(uniqueCount(records, "turno"), 0) },
      { label: "Registros sin factor", value: formatNumber(noFactorCount(records), 0), tone: "amber" },
    ],
    transporte_forestal: [
      { label: "km recorridos", value: formatNumber(sumField(records, "distancia_km"), 1) },
      { label: "Litros diesel", value: formatNumber(sumField(records, "litros_diesel", "cantidad"), 1) },
      { label: "m3 transportados", value: formatNumber(sumField(records, "carga_m3"), 1) },
      { label: "Emisiones estimadas", value: `${formatNumber(emissions, 1)} kg CO2e` },
    ],
    residuos_subproductos: [
      { label: "Cantidad total", value: formatNumber(sumField(records, "cantidad", "cantidad"), 1) },
      {
        label: "% valorizado",
        value: `${formatNumber(
          records.length
            ? (records.filter((record) => String(record?.metadata?.valorizado || "").toLowerCase().includes("si")).length / records.length) * 100
            : 0,
          1
        )}%`,
      },
      { label: "Tipos de residuo", value: formatNumber(uniqueCount(records, "tipo_residuo"), 0) },
      { label: "Gestores registrados", value: formatNumber(uniqueCount(records, "gestor"), 0) },
    ],
  };

  return definitions[moduleKey] || [];
}

function AserraderoOperationalKpis({ moduleKey, records = [] }) {
  const kpis = getKpis(moduleKey, records);

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi) => (
        <article
          key={kpi.label}
          className={`rounded-3xl border p-5 shadow-[0_14px_30px_rgba(15,23,42,0.05)] ${
            kpi.tone === "amber"
              ? "border-amber-200 bg-amber-50"
              : "border-[var(--border)] bg-[var(--bg-card)]"
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">
              {kpi.label}
            </p>
            <span className="rounded-2xl bg-emerald-100 p-2 text-emerald-700">
              <BarChart3 size={18} />
            </span>
          </div>
          <p className="mt-4 text-3xl font-black tracking-tight text-[var(--text-main)]">{kpi.value}</p>
        </article>
      ))}
    </section>
  );
}

export default AserraderoOperationalKpis;
