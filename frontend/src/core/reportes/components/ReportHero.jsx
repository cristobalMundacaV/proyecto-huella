import { Building2, Filter } from "lucide-react";

function ReportHero({ activeConstructora, filters, onOpenFilters, preset, report, reportConfig }) {
  const periodLabel = buildPeriodLabel(filters);
  const statusLabel = report.rows.length ? "Periodo con datos" : "Sin datos del periodo";
  const dataQuality = buildDataQualityDiagnosis(report.rows || []);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(236,253,245,0.92))] p-5 shadow-[var(--shadow-premium)] sm:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-emerald-700">
              <Building2 size={14} />
              {activeConstructora?.nombre || "Empresa activa"}
            </span>
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-sky-700">
              Preset: {preset.name}
            </span>
            <span className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">
              {periodLabel}
            </span>
          </div>

          <h1 className="mt-4 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
            {reportConfig.title}
          </h1>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-[var(--text-muted)]">
            {reportConfig.subtitle}
          </p>
          <p className="mt-5 max-w-4xl text-base leading-7 text-[var(--text-main)]">
            {report.executiveSummary}
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <span className={`rounded-2xl border px-4 py-3 text-sm font-black ${report.rows.length ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}`}>
            {statusLabel}
          </span>
          <span className={`rounded-2xl border px-4 py-3 text-sm font-black ${dataQuality.tone}`}>
            Calidad: {dataQuality.score}%
          </span>
          <button
            type="button"
            onClick={onOpenFilters}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-5 py-3 text-sm font-black text-emerald-700 shadow-[0_12px_24px_rgba(15,23,42,0.06)]"
          >
            <Filter size={18} />
            Filtros
          </button>
        </div>
      </div>

      <DataQualityPanel diagnosis={dataQuality} />

      {report.insights?.length > 0 && (
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {report.insights.slice(0, 4).map((insight) => (
            <div key={insight} className="rounded-2xl border border-[var(--border)] bg-white/80 p-4 text-sm font-semibold leading-6 text-[var(--text-main)]">
              {insight}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function DataQualityPanel({ diagnosis }) {
  return (
    <div className="mt-6 rounded-3xl border border-slate-200 bg-white/85 p-4 shadow-[0_10px_22px_rgba(15,23,42,0.04)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Calidad de datos ambientales</p>
          <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">{diagnosis.status}</h2>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-slate-600">{diagnosis.summary}</p>
        </div>
        <div className={`rounded-3xl border px-5 py-4 text-center ${diagnosis.tone}`}>
          <p className="text-[10px] font-black uppercase tracking-wide">Puntaje</p>
          <p className="mt-1 text-3xl font-black">{diagnosis.score}%</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <QualityMetric label="Registros" value={diagnosis.totalRecords} />
        <QualityMetric label="Con evidencia" value={`${diagnosis.evidencePct}%`} />
        <QualityMetric label="Sin factor" value={diagnosis.counts.withoutFactor} />
        <QualityMetric label="Sin vínculo" value={diagnosis.counts.withoutOperationalLink} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
        {diagnosis.priorities.length ? (
          diagnosis.priorities.map((item) => (
            <div key={item.key} className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-black text-amber-950">{item.label}</p>
                <span className="rounded-full border border-amber-200 bg-white px-2 py-1 text-[10px] font-black uppercase tracking-wide text-amber-700">{item.severity}</span>
              </div>
              <p className="mt-1 text-xs font-bold text-amber-800">{item.failed} registros afectados</p>
              <p className="mt-2 text-xs font-semibold leading-5 text-slate-600">{item.recommendation}</p>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-bold leading-6 text-emerald-800 xl:col-span-3">
            No hay brechas críticas de calidad en los registros del periodo. El reporte está mejor respaldado para análisis y toma de decisiones.
          </div>
        )}
      </div>
    </div>
  );
}

function QualityMetric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-center">
      <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-black text-slate-900">{value}</p>
    </div>
  );
}

function buildDataQualityDiagnosis(rows = []) {
  const totalRecords = rows.length;
  const checks = [
    {
      key: "withoutOperationalLink",
      label: "Registros sin obra o lote",
      weight: 2,
      failed: rows.filter((row) => !hasOperationalLink(row)).length,
      recommendation: "Vincular cada registro a una obra, lote o unidad operacional para mejorar trazabilidad.",
    },
    {
      key: "withoutStage",
      label: "Registros sin etapa o proceso",
      weight: 1.2,
      failed: rows.filter((row) => !hasAnyValue(row.etapa, row.etapa_nombre, row.metadata?.etapa, row.metadata?.proceso)).length,
      recommendation: "Completar etapa o proceso para entender dónde se concentra la huella.",
    },
    {
      key: "withoutSource",
      label: "Registros sin fuente o categoría",
      weight: 1.5,
      failed: rows.filter((row) => !hasAnyValue(row.fuente_emision, row.categoria)).length,
      recommendation: "Completar fuente de emisión y categoría para que el foco crítico sea confiable.",
    },
    {
      key: "withoutFactor",
      label: "Registros sin factor de emisión",
      weight: 2,
      failed: rows.filter((row) => !positiveNumber(row.factor_emision)).length,
      recommendation: "Asignar factor de emisión antes de usar el dato en reportes ejecutivos.",
    },
    {
      key: "invalidQuantity",
      label: "Cantidad inválida o faltante",
      weight: 2,
      failed: rows.filter((row) => !positiveNumber(row.cantidad)).length,
      recommendation: "Corregir cantidades en cero, negativas o vacías para evitar cálculos débiles.",
    },
    {
      key: "zeroEmissions",
      label: "CO₂e en cero o sin cálculo",
      weight: 2,
      failed: rows.filter((row) => !positiveNumber(row.emisiones_kg_co2e ?? row.emisiones)).length,
      recommendation: "Revisar cantidad, unidad y factor de emisión en registros sin CO₂e calculado.",
    },
    {
      key: "withoutEvidence",
      label: "Registros sin evidencia asociada",
      weight: 1,
      failed: rows.filter((row) => !row.evidencia_asociada).length,
      recommendation: "Respaldar registros relevantes con factura, guía, medición, foto o documento operacional.",
    },
  ];

  const totalWeight = checks.reduce((sum, check) => sum + check.weight, 0);
  const failedWeight = checks.reduce((sum, check) => sum + check.weight * check.failed, 0);
  const score = totalRecords ? Math.max(0, Math.round(100 - (failedWeight / (totalRecords * totalWeight)) * 100)) : 0;
  const evidencePct = totalRecords ? Math.round(((totalRecords - checks.find((check) => check.key === "withoutEvidence").failed) / totalRecords) * 100) : 0;
  const status = !totalRecords ? "Sin datos para evaluar" : score >= 85 ? "Datos confiables" : score >= 65 ? "Datos utilizables con observaciones" : "Datos débiles para decisión ejecutiva";
  const tone = !totalRecords ? "border-amber-200 bg-amber-50 text-amber-700" : score >= 85 ? "border-emerald-200 bg-emerald-50 text-emerald-700" : score >= 65 ? "border-amber-200 bg-amber-50 text-amber-700" : "border-rose-200 bg-rose-50 text-rose-700";
  const summary = !totalRecords
    ? "No existen registros en el periodo seleccionado. Primero se deben cargar datos ambientales."
    : score >= 85
      ? "Los registros del periodo tienen buena completitud para análisis, reportabilidad y decisiones ambientales."
      : "Existen brechas de completitud que deben corregirse antes de usar el reporte como respaldo formal.";

  const priorities = checks
    .filter((check) => check.failed > 0)
    .map((check) => ({ ...check, severity: check.weight >= 2 ? "Alta" : "Media", rate: totalRecords ? check.failed / totalRecords : 0 }))
    .sort((left, right) => right.weight * right.rate - left.weight * left.rate)
    .slice(0, 3);

  return {
    totalRecords,
    score,
    status,
    summary,
    tone,
    evidencePct,
    counts: checks.reduce((acc, check) => ({ ...acc, [check.key]: check.failed }), {}),
    priorities,
  };
}

function hasOperationalLink(row) {
  return hasAnyValue(row.obra, row.obra_codigo, row.obra_nombre, row.lote_forestal, row.lote_forestal_id, row.metadata?.lote, row.metadata?.obra_codigo);
}

function hasAnyValue(...values) {
  return values.some((value) => value !== null && value !== undefined && String(value).trim() !== "");
}

function positiveNumber(value) {
  return Number(value || 0) > 0;
}

function buildPeriodLabel(filters) {
  if (filters.fecha_inicio && filters.fecha_fin) return `${filters.fecha_inicio} a ${filters.fecha_fin}`;
  if (filters.fecha_inicio) return `Desde ${filters.fecha_inicio}`;
  if (filters.fecha_fin) return `Hasta ${filters.fecha_fin}`;
  return "Periodo completo";
}

export default ReportHero;
