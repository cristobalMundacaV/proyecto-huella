import { formatNumber } from "@/shared/utils/formatters";
import {
  constructionCategories,
  getConstructionCategoryLabel,
} from "@/features/lotes/utils/constructionEmissionCategories";
import {
  getConstructionWorkDocumentTypeLabel,
} from "@/shared/utils/constructionEvidenceLabels";
import { DetailItem } from "../common";

const recommendationByCategory = {
  Materiales:
    "Revisa hormigón, acero, áridos y proveedores para evaluar alternativas de menor carbono incorporado.",
  Transporte:
    "Evalúa proveedores más cercanos, consolidación de viajes y reducción de kilómetros recorridos.",
  Maquinaria:
    "Controla ralentí, consumo por equipo y mantención para reducir el impacto operativo.",
  Energía:
    "Revisa uso de generadores, consumo eléctrico y posibilidades de conexión temporal a red.",
  Residuos:
    "Separa residuos valorizables y mejora la trazabilidad de retiro para reducir disposición final.",
  Agua:
    "Monitorea consumo por etapa para detectar desviaciones y mejorar eficiencia.",
  Otros:
    "Clasifica mejor los registros para identificar acciones de reducción concretas.",
};

function ResumenTab({ balanceData, selectedLote }) {
  const activities = selectedLote.actividades || [];
  const documents = selectedLote.documentos || [];
  const totalEmissions = Number(
    balanceData?.emisiones_generadas_kg_co2e ||
      selectedLote.emisiones_kg_co2e ||
      0
  );
  const declaredSurface = Number(selectedLote.volumen_m3 || 0);
  const carbonIntensity =
    declaredSurface > 0 ? totalEmissions / declaredSurface : null;
  const activitiesWithCategories = activities.map((activity) => ({
    ...activity,
    categoria_visible: getConstructionCategoryLabel(
      activity.categoria,
      activity.actividad
    ),
  }));
  const categoryDistribution = constructionCategories
    .map((category) => {
      const emissions = activitiesWithCategories.reduce(
        (total, activity) =>
          activity.categoria_visible === category
            ? total + Number(activity.emisiones_kg_co2e || 0)
            : total,
        0
      );
      return {
        category,
        emissions,
        pct: totalEmissions > 0 ? (emissions / totalEmissions) * 100 : 0,
      };
    })
    .sort((left, right) => right.emissions - left.emissions);
  const criticalCategory =
    categoryDistribution.find((item) => item.emissions > 0)?.category || "Sin datos";
  const emissionsByStage = Object.values(
    activitiesWithCategories.reduce((accumulator, activity) => {
      const stage = activity.unidad_nombre || selectedLote.unidad_operativa_nombre || "Sin etapa";
      const current = accumulator[stage] || { stage, emissions: 0, records: 0 };
      current.emissions += Number(activity.emisiones_kg_co2e || 0);
      current.records += 1;
      accumulator[stage] = current;
      return accumulator;
    }, {})
  ).sort((left, right) => right.emissions - left.emissions);
  const criticalStage = emissionsByStage[0]?.stage || "Sin datos";
  const topSources = Object.values(
    activitiesWithCategories.reduce((accumulator, activity) => {
      const source = activity.actividad || "Sin fuente";
      const key = `${source}|${activity.categoria_visible}`;
      const current = accumulator[key] || {
        source,
        category: activity.categoria_visible,
        emissions: 0,
      };
      current.emissions += Number(activity.emisiones_kg_co2e || 0);
      accumulator[key] = current;
      return accumulator;
    }, {})
  )
    .sort((left, right) => right.emissions - left.emissions)
    .slice(0, 5);
  const environmentalStatus = getWorkEnvironmentalStatus({
    categoryDistribution,
    documents,
    totalEmissions,
  });
  const presentDocumentTypes = Array.from(
    new Set(documents.map((documento) => getConstructionWorkDocumentTypeLabel(documento.tipo_documento)))
  );
  const missingDocumentTypes = buildMissingDocumentSuggestions(activitiesWithCategories, presentDocumentTypes);
  const traceability = getDocumentTraceability({
    documents,
    missingDocumentTypes,
    activitiesWithCategories,
  });
  const mainRecommendation =
    totalEmissions > 0
      ? recommendationByCategory[criticalCategory] || recommendationByCategory.Otros
      : "Agrega registros de emisión para identificar las fuentes críticas de la obra.";

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
              Resumen ambiental de obra
            </p>
            <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">
              Inteligencia ambiental de construcción
            </h2>
          </div>
          <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${environmentalStatus.className}`}>
            <p>Estado ambiental de la obra</p>
            <p className="mt-1 text-lg">{environmentalStatus.label}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <DetailItem
            label="Emisiones de la obra"
            value={`${formatNumber(totalEmissions, 1)} kg CO2e`}
          />
          <DetailItem
            label="kg CO2e/m²"
            value={
              carbonIntensity != null
                ? `${formatNumber(carbonIntensity, 2)} kg CO2e/m²`
                : "Pendiente de superficie"
            }
          />
          <DetailItem label="Categoría crítica" value={criticalCategory} />
          <DetailItem label="Etapa crítica" value={criticalStage} />
          <DetailItem label="Registros de emisión" value={formatNumber(activities.length, 0)} />
          <DetailItem label="Evidencias asociadas" value={`${formatNumber(documents.length, 0)} documentos`} />
        </div>
        <p className="mt-3 text-sm text-[var(--text-muted)]">
          La intensidad relaciona emisiones registradas y superficie declarada de la obra.
        </p>
      </section>

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">Trazabilidad documental</p>
            <h3 className="mt-1 text-xl font-semibold text-[var(--text-main)]">{traceability.label}</h3>
            <p className="mt-2 text-sm text-[var(--text-muted)]">{traceability.description}</p>
          </div>
          <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${traceability.className}`}>
            Seguimiento interno
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">Tipos de documentos presentes</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {presentDocumentTypes.length ? presentDocumentTypes.map((type) => (
                <span key={type} className="rounded-full border border-[#B9D8D3] bg-[var(--info-bg)] px-3 py-1 text-xs font-bold text-[#075985]">{type}</span>
              )) : <span className="text-sm text-[var(--text-muted)]">Sin documentos cargados</span>}
            </div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">Documentos faltantes sugeridos</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {missingDocumentTypes.length ? missingDocumentTypes.map((type) => (
                <span key={type} className="rounded-full border border-[#E1C56F] bg-[var(--warning-bg)] px-3 py-1 text-xs font-bold text-[#7A4F00]">{type}</span>
              )) : <span className="text-sm text-[var(--text-muted)]">No hay faltantes críticos sugeridos</span>}
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Panel title="Emisiones por categoría">
          <div className="space-y-3">
            {categoryDistribution.map((item) => (
              <MetricBar
                key={item.category}
                label={item.category}
                pct={item.pct}
                value={`${formatNumber(item.emissions, 1)} kg CO2e`}
              />
            ))}
          </div>
        </Panel>

        <Panel title="Emisiones por etapa">
          <div className="space-y-3">
            {emissionsByStage.length ? (
              emissionsByStage.map((item) => (
                <MetricBar
                  key={item.stage}
                  detail={`${formatNumber(item.records, 0)} registros`}
                  label={item.stage}
                  pct={totalEmissions > 0 ? (item.emissions / totalEmissions) * 100 : 0}
                  value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                />
              ))
            ) : (
              <EmptyAnalysis />
            )}
          </div>
        </Panel>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Top fuentes críticas">
          <div className="space-y-3">
            {topSources.length ? (
              topSources.map((source, index) => (
                <div
                  key={`${source.source}-${source.category}`}
                  className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold text-[var(--primary-dark)]">
                        #{index + 1} · {source.category}
                      </p>
                      <p className="mt-1 font-semibold text-[var(--text-main)]">
                        {source.source}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-[#075985]">
                        {formatNumber(source.emissions, 1)} kg CO2e
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">
                        {formatNumber(
                          totalEmissions > 0 ? (source.emissions / totalEmissions) * 100 : 0,
                          1
                        )}
                        %
                      </p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <EmptyAnalysis />
            )}
          </div>
        </Panel>

        <Panel title="Recomendación principal">
          <p className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-4 text-sm font-medium leading-6 text-[var(--primary-dark)]">
            {mainRecommendation}
          </p>
          <div className="mt-3 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">
              Estado documental / evidencias
            </p>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              {documents.length
                ? `Evidencias asociadas: ${formatNumber(documents.length, 0)} documentos`
                : "Pendiente de vinculación documental"}
            </p>
          </div>
        </Panel>
      </section>
    </div>
  );
}

export default ResumenTab;

function getWorkEnvironmentalStatus({ categoryDistribution, documents, totalEmissions }) {
  if (!totalEmissions) {
    return {
      label: "Sin datos",
      className: "border-slate-300 bg-slate-100 text-slate-700",
    };
  }

  const maxShare = Math.max(...categoryDistribution.map((item) => item.pct || 0), 0);
  const activeCategories = categoryDistribution.filter((item) => item.emissions > 0).length;

  if (documents.length > 0 && maxShare <= 50) {
    return {
      label: "Respaldada",
      className: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    };
  }

  if (maxShare > 60) {
    return {
      label: "Crítica",
      className: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
    };
  }

  if (activeCategories >= 3) {
    return {
      label: "Alta trazabilidad",
      className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    };
  }

  return {
    label: "Inicial",
    className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
  };
}

function buildMissingDocumentSuggestions(activitiesWithCategories, presentDocumentTypes) {
  const suggestions = [];
  const hasCategory = (category) => activitiesWithCategories.some((activity) => activity.categoria_visible === category);
  const hasDocument = (documentType) => presentDocumentTypes.includes(documentType);
  const addMissing = (items) => {
    items.forEach((item) => {
      if (!suggestions.includes(item) && !hasDocument(item)) {
        suggestions.push(item);
      }
    });
  };

  if (hasCategory("Materiales")) {
    addMissing(["Factura de material", "Guía de despacho", "Ficha técnica de material"]);
  }

  if (hasCategory("Transporte")) {
    addMissing(["Guía de despacho", "Documento de transporte", "Ticket de pesaje"]);
  }

  if (hasCategory("Maquinaria")) {
    addMissing(["Factura de combustible", "Registro de maquinaria"]);
  }

  if (hasCategory("Energía")) {
    addMissing(["Boleta eléctrica", "Registro de generador"]);
  }

  if (hasCategory("Residuos")) {
    addMissing(["Ticket de pesaje", "Registro de retiro de residuos"]);
  }

  return suggestions.slice(0, 6);
}

function getDocumentTraceability({ documents, missingDocumentTypes, activitiesWithCategories }) {
  const validCount = documents.filter((documento) => ["validado", "validada"].includes(documento.estado_validacion || documento.estado_revision)).length;
  const observedCount = documents.filter((documento) => ["observada"].includes(documento.estado_revision)).length;
  const activeCategories = activitiesWithCategories.filter((activity) => activity.categoria_visible).length;

  if (documents.length === 0) {
    return {
      label: "Sin respaldo",
      description: "No hay evidencias asociadas a la obra.",
      className: "border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)]",
    };
  }

  if (observedCount > 0) {
    return {
      label: "En revisión",
      description: "Hay evidencias observadas o pendientes de ajuste.",
      className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
    };
  }

  if (missingDocumentTypes.length > 0) {
    return {
      label: "Inicial",
      description: "Existe respaldo documental, pero aún faltan documentos críticos por categoría.",
      className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
    };
  }

  if (validCount >= 3 && activeCategories >= 3) {
    return {
      label: "Alta trazabilidad",
      description: "La obra tiene evidencias validadas para varias categorías críticas.",
      className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    };
  }

  return {
    label: "Respaldada",
    description: "La obra cuenta con evidencias validadas para respaldar sus principales fuentes de emisión.",
    className: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
  };
}

function Panel({ children, title }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <h2 className="text-xl font-semibold text-[var(--text-main)]">{title}</h2>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function MetricBar({ detail, label, pct, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-[var(--text-main)]">{label}</p>
          {detail && <p className="mt-1 text-xs text-[var(--text-muted)]">{detail}</p>}
        </div>
        <div className="text-right">
          <p className="font-bold text-[#075985]">{value}</p>
          <p className="text-xs text-[var(--text-muted)]">{formatNumber(pct || 0, 1)}%</p>
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-[var(--primary)]"
          style={{ width: `${Math.max(0, Math.min(100, pct || 0))}%` }}
        />
      </div>
    </div>
  );
}

function EmptyAnalysis() {
  return (
    <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-sm text-[var(--text-muted)]">
      No hay registros de emisión suficientes.
    </p>
  );
}
