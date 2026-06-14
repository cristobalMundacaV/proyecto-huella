import { formatNumber } from "@/shared/utils/formatters";

import {
  getCriticalCategory,
  normalizeEmissionRows,
  sumEmissions,
} from "@/presets/shared/dashboardConfig";

function getConstructionRows(context) {
  return normalizeEmissionRows(context.dashboardData?.datos || context.rows || []);
}

function getCriticalWork(rows) {
  const byWork = rows.reduce((groups, row) => {
    const key = row.codigo_obra || row.obra_nombre || row.obra || "Sin obra";
    const current = groups[key] || { label: key, emissions: 0, surface: 0 };
    current.emissions += Number(row.emisiones || 0);
    current.surface += Number(row.superficie_m2 || row.superficie || 0);
    groups[key] = current;
    return groups;
  }, {});

  return Object.values(byWork).sort((left, right) => right.emissions - left.emissions)[0] || null;
}

function getCarbonIntensity(rows, totalEmissions) {
  const surface = rows.reduce((total, row) => total + Number(row.superficie_m2 || row.superficie || 0), 0);
  return surface > 0 ? totalEmissions / surface : null;
}

export const construccionDashboard = {
  title: "Panel principal de construccion",
  subtitle:
    "Convierte datos reales de obras, etapas, materiales y transporte en medicion, trazabilidad y decisiones para reducir emisiones durante la operacion.",
  kpis(context) {
    const rows = getConstructionRows(context);
    const total = Number(context.dashboardData?.total_emisiones ?? sumEmissions(rows));
    const criticalWork = context.dashboardData?.obra_critica || getCriticalWork(rows)?.label || "Sin datos";
    const criticalCategory = context.dashboardData?.categoria_critica || getCriticalCategory(rows)?.label || "Sin datos";
    const source = context.dashboardData?.fuente_critica || rows[0]?.fuente_emision || "Sin datos";
    const intensity = getCarbonIntensity(rows, total);

    return [
      { label: "Emisiones totales", value: `${formatNumber(total)} kg CO2e`, description: "Huella consolidada", icon: "activity", tone: "danger" },
      { label: "Obra critica", value: criticalWork, description: "Unidad con mayor impacto", icon: "factory", tone: "warning" },
      { label: "Categoria critica", value: criticalCategory, description: "Mayor concentracion por categoria", icon: "alert", tone: "violet" },
      { label: "Fuente critica", value: source, description: "Fuente prioritaria de intervencion", icon: "target", tone: "danger" },
      { label: "Evidencia respaldada", value: context.dashboardData?.evidencia_respaldada ? `${formatNumber(context.dashboardData.evidencia_respaldada, 0)}%` : "Pendiente de vinculacion", description: "Respaldo documental", icon: "database", tone: "success" },
      { label: "Intensidad de carbono", value: intensity != null ? `${formatNumber(intensity, 2)} kg CO2e/m2` : "Pendiente de superficie", description: "Emisiones por superficie", icon: "gauge", tone: "info" },
    ];
  },
  modules(context) {
    return context.categoryGroups.map((group) => ({
      key: group.key,
      label: group.label,
      records: group.records,
      emissions: group.emissions,
      mainValue: `${formatNumber(group.emissions, 1)} kg CO2e`,
      missingFactors: group.rows.filter((row) => !Number(row.factor_emision || 0)).length,
    }));
  },
  criticalDrivers(context) {
    return {
      category: context.criticalCategory?.label || "Sin datos",
      module: context.criticalModule?.label || "Obras y etapas",
      source: context.dashboardData?.fuente_critica || context.rows[0]?.fuente_emision || "Sin datos",
      concentration: context.totalEmissions > 0 ? ((context.criticalCategory?.emissions || 0) / context.totalEmissions) * 100 : 0,
      recommendation: "Priorizar la categoria y la obra con mayor concentracion antes de ampliar acciones de reduccion.",
    };
  },
  recommendationBuilder(context) {
    const category = context.criticalCategory?.label || "Sin datos";
    return {
      title: "Siguiente decision recomendada",
      description: `Revisar los registros de ${category} con mayor impacto, validar evidencia y asociar acciones de reduccion por obra o etapa.`,
      actions: ["Validar factor de emision", "Adjuntar evidencia", "Comparar fuente critica contra avance de obra"],
    };
  },
};
