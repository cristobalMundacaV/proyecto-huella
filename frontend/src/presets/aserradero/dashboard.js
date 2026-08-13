import { formatNumber } from "@/shared/utils/formatters";

import { aserraderoModules } from "./operationalConfig";

const moduleLabels = {
  recepcion_trozas: "Recepcion de trozas",
  produccion: "Produccion",
  secado: "Secado",
  energia: "Energia",
  transporte_forestal: "Transporte forestal",
  residuos_subproductos: "Residuos / Subproductos",
};

const moduleOrder = Object.keys(aserraderoModules);

const num = (row, field, fallback = 0) => Number(row?.metadata?.[field] ?? row?.[field] ?? fallback) || 0;
const sum = (rows, field, fallbackField = null) =>
  rows.reduce((total, row) => total + num(row, field, fallbackField ? row?.[fallbackField] : 0), 0);
const avg = (rows, field) => {
  const values = rows.map((row) => num(row, field)).filter((value) => value > 0);
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
};

function getAserraderoRows(context) {
  return context.rows.filter((row) => row.metadata?.preset === "forestal");
}

function moduleRows(rows, moduleKey) {
  return rows.filter((row) => row.metadata?.module === moduleKey);
}

export const aserraderoDashboard = {
  title: "Inteligencia ambiental para operacion forestal",
  subtitle:
    "Controla recepcion de trozas, produccion, secado, energia, transporte y valorizacion de residuos.",
  kpis(context) {
    const rows = getAserraderoRows(context);
    const recepcion = moduleRows(rows, "recepcion_trozas");
    const produccion = moduleRows(rows, "produccion");
    const energia = moduleRows(rows, "energia");
    const secado = moduleRows(rows, "secado");
    const transporte = moduleRows(rows, "transporte_forestal");
    const residuos = moduleRows(rows, "residuos_subproductos");
    const valorizados = residuos.filter((row) => String(row.metadata?.valorizado || "").toLowerCase().includes("si")).length;
    const lotesForestales = context.safeDashboardData?.lotes_forestales || context.lotes_forestales || {};

    return [
      { label: "Huella total", value: `${formatNumber(context.totalEmissions, 1)} kg CO2e`, description: "Registros forestales calculados", icon: "leaf", tone: "danger" },
      { label: "Lotes forestales", value: formatNumber(lotesForestales.total_lotes || 0, 0), description: "Lotes con trazabilidad forestal", icon: "package", tone: "success" },
      { label: "CO2 almacenado", value: `${formatNumber(lotesForestales.co2_almacenado_kg || 0, 1)} kg`, description: "Carbono retenido por lotes", icon: "leaf", tone: "success" },
      { label: "Balance neto", value: `${formatNumber(lotesForestales.balance_neto_kg_co2e || 0, 1)} kg`, description: "Emisiones menos CO2 almacenado", icon: "gauge", tone: "info" },
      { label: "Balance favorable", value: formatNumber(lotesForestales.lotes_balance_favorable || 0, 0), description: "Lotes con balance negativo", icon: "target", tone: "success" },
      { label: "Criticos / incompletos", value: `${formatNumber(lotesForestales.lotes_balance_critico || 0, 0)} / ${formatNumber(lotesForestales.lotes_balance_incompleto || 0, 0)}`, description: "Lotes a revisar", icon: "alert", tone: "warning" },
      { label: "m3 recibidos", value: formatNumber(sum(recepcion, "volumen_m3", "cantidad"), 1), description: "Materia prima registrada", icon: "package", tone: "success" },
      { label: "m3 procesados", value: formatNumber(sum(produccion, "volumen_entrada_m3", "cantidad"), 1), description: "Volumen de aserrio", icon: "factory", tone: "info" },
      { label: "Rendimiento promedio", value: `${formatNumber(avg(produccion, "rendimiento_pct"), 1)}%`, description: "Entrada versus salida", icon: "gauge", tone: "success" },
      { label: "Energia registrada", value: `${formatNumber(sum([...energia, ...secado], "consumo_kwh", "cantidad"), 1)} kWh`, description: "Consumo declarado", icon: "zap", tone: "warning" },
      { label: "Transporte forestal", value: `${formatNumber(sum(transporte, "litros_diesel", "cantidad"), 1)} L`, description: "Combustible registrado", icon: "truck", tone: "warning" },
      { label: "Residuos valorizados", value: `${formatNumber(residuos.length ? (valorizados / residuos.length) * 100 : 0, 1)}%`, description: "Registros con valorizacion", icon: "recycle", tone: "success" },
      { label: "Registros sin factor", value: formatNumber(context.recordsWithoutFactor.length, 0), description: "Pendientes de calculo ambiental", icon: "alert", tone: "danger" },
    ];
  },
  modules(context) {
    const rows = getAserraderoRows(context);
    return moduleOrder.map((moduleKey) => {
      const currentRows = moduleRows(rows, moduleKey);
      const emissions = currentRows.reduce((total, row) => total + Number(row.emisiones || 0), 0);
      const missingFactors = currentRows.filter((row) => !Number(row.factor_emision || 0)).length;
      const operationalValue = {
        recepcion_trozas: `${formatNumber(sum(currentRows, "volumen_m3", "cantidad"), 1)} m3 recibidos`,
        produccion: `${formatNumber(sum(currentRows, "volumen_entrada_m3", "cantidad"), 1)} m3 procesados`,
        secado: `${formatNumber(sum(currentRows, "energia_kwh", "cantidad"), 1)} kWh`,
        energia: `${formatNumber(sum(currentRows, "consumo_kwh", "cantidad"), 1)} kWh`,
        transporte_forestal: `${formatNumber(sum(currentRows, "distancia_km"), 1)} km`,
        residuos_subproductos: `${formatNumber(sum(currentRows, "cantidad", "cantidad"), 1)} registrados`,
      }[moduleKey];

      return {
        key: moduleKey,
        label: moduleLabels[moduleKey],
        records: currentRows.length,
        emissions,
        mainValue: operationalValue,
        missingFactors,
      };
    });
  },
  criticalDrivers(context) {
    const source = context.rows.find((row) => Number(row.emisiones || 0) === Math.max(...context.rows.map((item) => Number(item.emisiones || 0)), 0))?.fuente_emision || "Sin datos";
    return {
      category: context.criticalCategory?.label || "Sin datos",
      module: moduleLabels[context.criticalModule?.key] || "Sin modulo",
      source,
      concentration: context.totalEmissions > 0 ? ((context.criticalModule?.emissions || 0) / context.totalEmissions) * 100 : 0,
      recommendation: "Concentrar la primera mejora en el modulo forestal que domina la huella.",
    };
  },
  recommendationBuilder(context) {
    const moduleKey = context.criticalModule?.key || "";
    const byModule = {
      transporte_forestal: "Controlar litros, rutas, carga transportada y viajes vacios para reducir emisiones logisticas.",
      energia: "Separar consumo por area, turno y medidor para identificar consumos criticos.",
      secado: "Medir kWh por camara, horas de secado y humedad final para mejorar eficiencia termica.",
      residuos_subproductos: "Aumentar valorizacion y separar aserrin, corteza, despuntes y rechazos no aprovechados.",
      produccion: "Medir rendimiento entrada/salida y merma por lote para mejorar conversion de materia prima.",
      recepcion_trozas: "Completar trazabilidad de origen, especie, volumen y humedad para cerrar linea base forestal.",
    };

    return {
      title: "Recomendacion operativa forestal",
      description: byModule[moduleKey] || "Completar registros por modulo y asociar factores de emision para activar lectura ambiental.",
      actions: ["Revisar registros sin factor", "Completar metadata operacional", "Adjuntar evidencia del modulo critico"],
    };
  },
};
