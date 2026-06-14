import { formatNumber } from "@/shared/utils/formatters";

const num = (row, field, fallback = 0) => Number(row?.metadata?.[field] ?? row?.[field] ?? fallback) || 0;

export const industrialDashboard = {
  title: "Panel ambiental industrial",
  subtitle: "Prepara la lectura de energia, procesos, residuos, agua y evidencia para operaciones industriales.",
  kpis(context) {
    const rows = context.rows.filter((row) => row.metadata?.preset === "industrial");
    const energy = rows.reduce((total, row) => total + num(row, "consumo_kwh"), 0);
    const water = rows.reduce((total, row) => total + num(row, "agua_m3"), 0);
    const residues = rows.reduce((total, row) => total + num(row, "residuos_kg", row.cantidad), 0);
    const processes = new Set(rows.map((row) => row.metadata?.proceso || row.fuente_emision).filter(Boolean)).size;
    return [
      { label: "Huella total", value: `${formatNumber(context.totalEmissions, 1)} kg CO2e`, description: "Emisiones industriales", icon: "factory", tone: "danger" },
      { label: "Consumo energetico", value: `${formatNumber(energy, 1)} kWh`, description: "Energia registrada", icon: "zap", tone: "warning" },
      { label: "Procesos registrados", value: formatNumber(processes, 0), description: "Procesos con actividad", icon: "database", tone: "info" },
      { label: "Residuos generados", value: `${formatNumber(residues, 1)} kg`, description: "Masa declarada", icon: "recycle", tone: "warning" },
      { label: "Agua registrada", value: `${formatNumber(water, 1)} m3`, description: "Consumo hidrico", icon: "droplets", tone: "info" },
      { label: "Categoria critica", value: context.criticalCategory?.label || "Sin datos", description: "Mayor concentracion", icon: "target", tone: "violet" },
      { label: "Registros sin factor", value: formatNumber(context.recordsWithoutFactor.length, 0), description: "Pendientes de calculo", icon: "alert", tone: "danger" },
      { label: "Evidencia respaldada", value: context.dashboardData?.evidencia_respaldada ? `${formatNumber(context.dashboardData.evidencia_respaldada, 0)}%` : "Pendiente", description: "Respaldo documental", icon: "database", tone: "success" },
    ];
  },
  modules(context) {
    return context.categoryGroups;
  },
  criticalDrivers(context) {
    return {
      category: context.criticalCategory?.label || "Sin datos",
      module: context.criticalModule?.label || "Sin modulo",
      source: context.rows[0]?.fuente_emision || "Sin datos",
      concentration: context.totalEmissions > 0 ? ((context.criticalCategory?.emissions || 0) / context.totalEmissions) * 100 : 0,
      recommendation: "Separar consumos por proceso, energia, agua y residuos para activar gestion industrial.",
    };
  },
  recommendationBuilder() {
    return {
      title: "Base industrial preparada",
      description: "El dashboard esta listo para recibir registros industriales por metadata sin cambios de backend.",
      actions: ["Separar procesos", "Completar energia y agua", "Clasificar residuos"],
    };
  },
};
