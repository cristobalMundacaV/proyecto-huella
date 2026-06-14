import { formatNumber } from "@/shared/utils/formatters";

const num = (row, field) => Number(row?.metadata?.[field] ?? row?.[field] ?? 0) || 0;

export const transporteDashboard = {
  title: "Panel ambiental logistico",
  subtitle: "Prepara la lectura de flota, viajes, combustible, rutas y mantenciones para el preset transporte.",
  kpis(context) {
    const rows = context.rows.filter((row) => row.metadata?.preset === "transporte");
    const km = rows.reduce((total, row) => total + num(row, "distancia_km"), 0);
    const litros = rows.reduce((total, row) => total + num(row, "litros_combustible"), 0);
    const vehiculos = new Set(rows.map((row) => row.metadata?.patente || row.metadata?.vehiculo).filter(Boolean)).size;
    const viajes = new Set(rows.map((row) => row.metadata?.viaje_id).filter(Boolean)).size || rows.length;
    return [
      { label: "Huella total", value: `${formatNumber(context.totalEmissions, 1)} kg CO2e`, description: "Emisiones logisticas", icon: "truck", tone: "danger" },
      { label: "km recorridos", value: formatNumber(km, 1), description: "Distancia registrada", icon: "route", tone: "info" },
      { label: "Litros combustible", value: formatNumber(litros, 1), description: "Consumo declarado", icon: "fuel", tone: "warning" },
      { label: "Vehiculos registrados", value: formatNumber(vehiculos, 0), description: "Flota con actividad", icon: "factory", tone: "neutral" },
      { label: "Viajes registrados", value: formatNumber(viajes, 0), description: "Eventos logisticos", icon: "database", tone: "info" },
      { label: "Emisiones por km", value: km > 0 ? `${formatNumber(context.totalEmissions / km, 2)} kg/km` : "Sin km", description: "Intensidad logistica", icon: "gauge", tone: "success" },
      { label: "Rutas criticas", value: context.criticalModule?.label || "Sin datos", description: "Concentracion por ruta", icon: "target", tone: "warning" },
      { label: "Registros sin factor", value: formatNumber(context.recordsWithoutFactor.length, 0), description: "Pendientes de factor", icon: "alert", tone: "danger" },
    ];
  },
  modules(context) {
    return context.moduleGroups;
  },
  criticalDrivers(context) {
    return {
      category: context.criticalCategory?.label || "Sin datos",
      module: context.criticalModule?.label || "Sin modulo",
      source: context.rows[0]?.fuente_emision || "Sin datos",
      concentration: context.totalEmissions > 0 ? ((context.criticalModule?.emissions || 0) / context.totalEmissions) * 100 : 0,
      recommendation: "Registrar viajes con km, combustible, patente y ruta para activar diagnostico logistico.",
    };
  },
  recommendationBuilder() {
    return {
      title: "Flujo logistico preparado",
      description: "El dashboard ya acepta metadata del preset transporte. Los modulos reales pueden conectarse sin cambiar endpoints.",
      actions: ["Registrar km y combustible", "Separar rutas frecuentes", "Asociar vehiculo y viaje"],
    };
  },
};
