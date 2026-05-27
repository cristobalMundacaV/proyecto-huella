import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Database,
  Factory,
  Leaf,
  Menu,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import Sidebar from "@/layouts/Sidebar";
import KpiCard from "@/shared/components/KpiCard";
import LoginPage from "@/features/auth/pages/LoginPage";
import ExecutiveSummary from "@/features/dashboard/components/ExecutiveSummary";
import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
import EmisionesView from "@/features/emisiones/EmisionesView";
import ConstructorasView from "@/features/constructoras/pages/ConstructorasPage";
import EvidenciasPage from "@/features/evidencias/pages/EvidenciasPage";
import ConfiguracionPage from "@/features/configuracion/pages/ConfiguracionPage";
import FactoresView from "@/features/factores/pages/FactoresPage";
import ImportacionesView from "@/features/importaciones/pages/ImportacionesPage";
import ObrasView from "@/features/obras/pages/ObrasPage";
import EtapasObraView from "@/features/etapas/pages/EtapasPage";
import ReportesView from "@/features/reportes/pages/ReportesView";
import UsuariosPage from "@/features/usuarios/pages/UsuariosPage";
import {
  getConstructoraDashboard,
  getConstructoraEmisiones,
  getConstructoraEstado,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import { calculateRiskProfile } from "@/features/dashboard/utils/risk";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { useAuth } from "@/features/auth/context/AuthContext";
import {
  constructionCategories,
  getConstructionCategoryLabel,
} from "@/features/obras/utils/constructionEmissionCategories";

const viewTransition = {
  duration: 0.24,
  ease: [0.22, 1, 0.36, 1],
};

const DASHBOARD_REFRESH_INTERVAL_MS = 10000;

const operationalCategoryOrder = [
  "Materiales",
  "Residuos",
  "Maquinaria",
  "Energia",
  "Transporte",
  "Agua",
  "Otros",
];

const operationalCategoryDisplayNames = {
  Energia: "Energía",
};

const operationalIntelligence = {
  Materiales: {
    priority: "Prioridad máxima",
    relevanceLabel: "Foco crítico de intervención",
    diagnosis:
      "Materiales concentra el mayor impacto ambiental de la obra. La reducción debe enfocarse en acero estructural, hormigón y cemento antes de nuevas compras.",
    mainAction:
      "Revisar factores de emisión de proveedores y validar alternativas con menor huella.",
    actions: [
      "Solicitar factores de emisión a proveedores.",
      "Comparar proveedores alternativos.",
      "Revisar cubicaciones.",
      "Detectar sobreconsumo.",
      "Pedir fichas técnicas o EPD.",
      "Medir merma de materiales.",
    ],
    metrics: [
      "kg CO2e / ton de acero",
      "kg CO2e / m³ de hormigón",
      "kg CO2e / ton de cemento",
      "% merma por material",
      "% compras con ficha técnica o EPD",
    ],
    evidence: [
      "Fichas técnicas",
      "EPD o declaración ambiental",
      "Facturas",
      "Guías de despacho",
      "Cubicaciones",
      "Comparativo de proveedores",
    ],
    nextStep:
      "Ejecutar un piloto comparando el proveedor actual contra alternativas con menor factor de emisión antes de nuevas compras.",
  },
  Transporte: {
    priority: "Control táctico",
    relevanceLabel: "Reducción logística de rápida ejecución",
    diagnosis:
      "Transporte no es el principal foco de emisión, pero puede entregar reducciones rápidas si se consolidan viajes y se priorizan proveedores cercanos. Debe mantenerse como línea de control operativo, no como intervención principal.",
    mainAction: "Consolidar viajes y reducir kilómetros improductivos.",
    actions: [
      "Consolidar viajes.",
      "Evitar despachos pequeños.",
      "Priorizar proveedores cercanos.",
      "Registrar origen, destino, km, patente, carga y litros.",
      "Revisar camiones con baja carga útil.",
    ],
    metrics: [
      "km por viaje",
      "litros por traslado",
      "carga útil promedio",
      "% viajes consolidados",
    ],
    evidence: [
      "Guías de despacho",
      "Registros de ruta",
      "Patentes",
      "Kilometraje",
      "Facturas de combustible",
      "Plan de abastecimiento",
    ],
    nextStep:
      "Consolidar despachos con proveedores cercanos y medir la reducción de kilómetros antes de escalar el ajuste logístico.",
  },
  Maquinaria: {
    priority: "Control operativo",
    relevanceLabel: "Eficiencia de faena y consumo diésel",
    diagnosis:
      "Maquinaria no domina la huella, pero sí puede mejorar la eficiencia de obra. La primera medida no es cambiar equipos: es medir litros por equipo, reducir ralentí y ordenar la planificación diaria.",
    mainAction: "Medir litros por equipo y bajar tiempos sin producción.",
    actions: [
      "Medir litros por equipo.",
      "Controlar maquinaria encendida sin producción.",
      "Registrar horas máquina.",
      "Agrupar tareas.",
      "Revisar mantenciones.",
      "Evaluar equipos eléctricos solo si existe uso intensivo o repetitivo.",
    ],
    metrics: [
      "litros por equipo",
      "horas máquina",
      "% tiempo en ralentí",
      "consumo por frente",
    ],
    evidence: [
      "Partes de máquina",
      "Bitácoras de consumo",
      "Horómetros",
      "Registros de mantención",
      "Informe de producción diaria",
    ],
    nextStep:
      "Separar consumo por equipo y frente de trabajo para identificar dónde se pierde eficiencia antes de cambiar la flota.",
  },
  Energia: {
    priority: "Control de faena",
    relevanceLabel: "Gestión de consumo eléctrico y generadores",
    diagnosis:
      "Energía debe gestionarse como control de faena. El foco es reducir generador, ordenar horarios de consumo y separar consumos por frente para detectar desviaciones.",
    mainAction:
      "Separar red, generador y consumos por frente para encontrar desviaciones.",
    actions: [
      "Separar electricidad de red versus generador.",
      "Reducir uso de generador.",
      "Revisar equipos encendidos fuera de horario.",
      "Medir consumo semanal.",
      "Definir horarios de iluminación y herramientas.",
      "Evaluar conexión provisoria si el generador es constante.",
    ],
    metrics: [
      "kWh semanal",
      "litros de generador",
      "consumo por frente",
      "% consumo fuera de horario",
    ],
    evidence: [
      "Boletas eléctricas",
      "Registros de generador",
      "Lecturas semanales",
      "Bitácora de turnos",
    ],
    nextStep:
      "Separar consumos por fuente y frente para detectar desviaciones y definir si la conexión provisoria reemplaza al generador.",
  },
  Residuos: {
    priority: "Trazabilidad prioritaria",
    relevanceLabel: "Segregación, destino y valorización",
    diagnosis:
      "Residuos debe convertirse en una línea de trazabilidad. La meta no es solo bajar kg CO2e, sino demostrar segregación, destino y valorización con evidencia documental.",
    mainAction:
      "Separar residuos y asegurar respaldo documental del destino final.",
    actions: [
      "Separar residuos mixtos, fierro, madera, plástico, cartón, yeso-cartón y escombros.",
      "Reducir residuos mixtos.",
      "Pedir tickets de pesaje.",
      "Pedir certificado del gestor.",
      "Registrar destino final.",
      "Implementar contenedores diferenciados.",
    ],
    metrics: [
      "ton de residuos mixtos",
      "% valorizado",
      "% segregación efectiva",
      "tickets de pesaje validados",
    ],
    evidence: [
      "Tickets de pesaje",
      "Certificado del gestor",
      "Manifiestos de retiro",
      "Registros de segregación",
      "Fotos de contenedores",
    ],
    nextStep:
      "Asegurar segregación en origen y validar el destino documental antes de considerar la categoría como controlada.",
  },
  Agua: {
    priority: "Monitoreo continuo",
    relevanceLabel: "Control operativo sin impacto carbono inmediato",
    diagnosis:
      "Agua no requiere intervención inmediata en carbono, pero debe mantenerse monitoreada para control operativo y futuras métricas ambientales.",
    mainAction:
      "Mantener trazabilidad del consumo para detectar desviaciones y fugas.",
    actions: [
      "Registrar consumo si existen camiones aljibe.",
      "Medir consumo semanal.",
      "Detectar fugas.",
      "Asociar consumo a etapas de obra.",
      "Controlar procesos húmedos.",
    ],
    metrics: [
      "m³ semanales",
      "consumo por etapa",
      "% desviación respecto de plan",
      "eventos de fuga",
    ],
    evidence: [
      "Lecturas de agua",
      "Boletas o guías de aljibe",
      "Bitácora semanal",
      "Registros por etapa",
    ],
    nextStep:
      "Mantener el seguimiento semanal y asociar cada consumo a la etapa de obra correspondiente para preparar futuras métricas ambientales.",
  },
  Otros: {
    priority: "Clasificación pendiente",
    relevanceLabel: "Fuente a depurar",
    diagnosis:
      "Otros no debe usarse como categoría principal. Si aparecen emisiones aquí, el sistema debe revisar si existen registros mal clasificados o factores de emisión faltantes.",
    mainAction:
      "Revisar la clasificación para evitar que información relevante quede sin categoría.",
    actions: [
      "Revisar registros clasificados como Otros.",
      "Reasignar emisiones a categorías correctas.",
      "Detectar factores de emisión faltantes.",
      "Evitar que datos importantes queden sin clasificación.",
    ],
    metrics: [
      "% registros sin clasificar",
      "factores faltantes",
      "% reasignación correcta",
    ],
    evidence: [
      "Registros fuente",
      "Catálogo de factores",
      "Historial de clasificación",
      "Notas de corrección",
    ],
    nextStep:
      "Depurar la clasificación y mover las emisiones a su categoría correcta antes de cerrar el periodo de análisis.",
  },
};

const stageOperationalOrder = [
  "Fundaciones",
  "Obra gruesa",
  "Terminaciones",
  "Retiro de residuos",
  "Excavación y movimiento de tierra",
  "Instalaciones",
];

const stageOperationalIntelligence = {
  fundaciones: {
    label: "Fundaciones",
    priority: "Etapa crítica principal",
    relevanceLabel: "Foco prioritario de intervención",
    diagnosis:
      "Fundaciones concentra el mayor impacto de la obra. La reducción debe enfocarse en validar cantidades reales de hormigón, cemento y áridos, controlar sobreconsumo y comparar proveedores antes de nuevas compras.",
    mainAction:
      "Ejecutar un piloto de materiales de menor carbono para fundaciones.",
    actions: [
      "Revisar cubicación real versus material comprado.",
      "Comparar proveedor actual de hormigón y cemento contra alternativas con menor factor de emisión.",
      "Solicitar ficha técnica o declaración ambiental del hormigón y cemento utilizados.",
      "Revisar sobreconsumo, merma o reprocesos en fundaciones.",
      "Validar guías de despacho y facturas contra cantidades realmente ejecutadas.",
    ],
    metrics: [
      "kg CO2e / m³ de hormigón",
      "kg CO2e / ton de cemento",
      "m³ comprados vs m³ ejecutados",
      "% merma de material",
      "% documentación respaldada",
    ],
    evidence: [
      "Cubicaciones",
      "Guías de despacho",
      "Facturas",
      "Fichas técnicas",
      "EPD o declaraciones ambientales",
      "Registro de cantidades ejecutadas",
    ],
    nextStep:
      "Validar cantidades reales de hormigón, cemento y áridos antes de nuevas compras, comparando proveedores con menor factor de emisión.",
  },
  "obra gruesa": {
    label: "Obra gruesa",
    priority: "Etapa crítica secundaria",
    relevanceLabel: "Carga casi equivalente a fundaciones",
    diagnosis:
      "Obra gruesa mantiene una carga casi equivalente a Fundaciones. La intervención debe enfocarse en acero estructural y hormigón, priorizando proveedores con menor factor de emisión y controlando mermas antes de escalar a cambios mayores.",
    mainAction:
      "Priorizar revisión de acero estructural y hormigón con control de merma y proveedores.",
    actions: [
      "Revisar acero estructural como fuente principal.",
      "Solicitar factor kg CO2e/ton al proveedor de acero.",
      "Comparar proveedor actual contra alternativas con contenido reciclado o menor huella.",
      "Controlar merma, despuntes y reprocesos.",
      "Separar emisiones de acero, hormigón y energía para no mezclar decisiones.",
      "Revisar consumo energético o generador asociado a esta etapa.",
    ],
    metrics: [
      "kg CO2e / ton de acero",
      "toneladas de acero comprado versus instalado",
      "% merma de acero",
      "kg CO2e / m² acumulado en obra gruesa",
      "evidencias por proveedor",
    ],
    evidence: [
      "Facturas de acero",
      "Guías de despacho",
      "Certificados del proveedor",
      "Fichas técnicas",
      "Comparativo de proveedores",
      "Registro de despuntes o merma",
    ],
    nextStep:
      "Priorizar una revisión del acero estructural y del hormigón utilizado en obra gruesa, separando cantidades compradas, instaladas y desperdiciadas.",
  },
  terminaciones: {
    label: "Terminaciones",
    priority: "Impacto menor controlable",
    relevanceLabel: "Control operativo de etapa final",
    diagnosis:
      "Terminaciones no domina la huella, pero puede mejorar el control operativo. La recomendación es reducir merma, consolidar compras y exigir fichas técnicas para materiales recurrentes.",
    mainAction:
      "Ordenar compras de terminaciones y reducir desperdicios por cortes o reprocesos.",
    actions: [
      "Revisar yeso-cartón, pinturas, revestimientos, adhesivos y terminaciones recurrentes.",
      "Solicitar fichas técnicas de materiales de uso frecuente.",
      "Evitar compras fraccionadas que generen transporte innecesario.",
      "Controlar desperdicio por cortes, errores o reprocesos.",
      "Consolidar pedidos por etapa o frente.",
    ],
    metrics: [
      "kg CO2e / m² terminado",
      "% merma por material",
      "compras con ficha técnica",
      "residuos generados por terminaciones",
      "cantidad de compras fraccionadas",
    ],
    evidence: [
      "Facturas",
      "Fichas técnicas",
      "Guías de despacho",
      "Registro de mermas",
      "Registro de residuos por terminaciones",
    ],
    nextStep:
      "Ordenar las compras de terminaciones y reducir desperdicios por cortes, errores o reprocesos.",
  },
  "retiro de residuos": {
    label: "Retiro de residuos",
    priority: "Trazabilidad ambiental",
    relevanceLabel: "Segregación y valorización verificable",
    diagnosis:
      "Retiro de residuos debe gestionarse como trazabilidad ambiental. La prioridad es separar residuos, reducir disposición final y respaldar cada retiro con ticket de pesaje y certificado del gestor.",
    mainAction:
      "Convertir cada retiro en un registro verificable con peso, tipo de residuo, gestor y destino.",
    actions: [
      "Separar residuos mixtos, escombros, fierro, cartón, plástico y madera.",
      "Evitar que todo termine como residuo mixto.",
      "Exigir ticket de pesaje por retiro.",
      "Registrar gestor, destino y tipo de tratamiento.",
      "Medir porcentaje valorizado.",
      "Implementar contenedores diferenciados por frente o etapa.",
    ],
    metrics: [
      "toneladas de residuos mixtos",
      "toneladas de residuos valorizados",
      "% valorización",
      "tickets de pesaje",
      "kg CO2e / tonelada retirada",
    ],
    evidence: [
      "Tickets de pesaje",
      "Certificados del gestor",
      "Registro de retiro",
      "Fotografías de segregación",
      "Comprobantes de valorización o disposición final",
    ],
    nextStep:
      "Convertir cada retiro en un registro verificable con peso, tipo de residuo, gestor, destino y respaldo documental.",
  },
  "excavacion y movimiento de tierra": {
    label: "Excavación y movimiento de tierra",
    priority: "Quick win operativo",
    relevanceLabel: "Eficiencia de maquinaria y diésel",
    diagnosis:
      "Excavación tiene una huella baja frente a materiales, pero es una etapa ideal para quick wins: medir litros por equipo, reducir ralentí y mejorar la planificación diaria de maquinaria.",
    mainAction:
      "Medir consumo real por equipo y reducir horas improductivas antes de considerar cambios mayores.",
    actions: [
      "Medir litros por equipo.",
      "Controlar ralentí de excavadora, retroexcavadora y maquinaria pesada.",
      "Agrupar tareas para evitar movimientos repetidos.",
      "Revisar mantención preventiva.",
      "Registrar horas máquina por frente.",
      "Evitar traslados innecesarios dentro de la obra.",
    ],
    metrics: [
      "litros / hora máquina",
      "kg CO2e / hora máquina",
      "horas improductivas",
      "litros por frente",
      "mantenciones realizadas",
      "horas máquina planificadas versus reales",
    ],
    evidence: [
      "Registro de combustible",
      "Horómetro",
      "Parte diario de maquinaria",
      "Mantenciones",
      "Registro de frente de trabajo",
    ],
    nextStep:
      "Medir consumo real por equipo y reducir horas improductivas antes de considerar cambios mayores de maquinaria.",
  },
  instalaciones: {
    label: "Instalaciones",
    priority: "Monitoreo operativo",
    relevanceLabel: "Seguimiento del consumo energético de la etapa",
    diagnosis:
      "La etapa de Instalaciones no requiere una intervención prioritaria en este momento. Sin embargo, debe mantenerse bajo monitoreo para evitar aumentos innecesarios en el consumo eléctrico y en el uso de generadores durante la ejecución.",
    mainAction:
      "Separar electricidad de red y generador para detectar desviaciones antes de que crezca el impacto.",
    actions: [
      "Separar el consumo eléctrico proveniente de la red y del generador.",
      "Revisar equipos, herramientas e iluminación que permanezcan encendidos fuera de horario.",
      "Registrar semanalmente el consumo de kWh por frente de trabajo.",
      "Reducir el uso de generadores cuando exista una alternativa eléctrica disponible.",
      "Vincular boletas eléctricas, registros de consumo o respaldos operativos.",
      "Controlar herramientas eléctricas, iluminación temporal y tableros utilizados en faena.",
    ],
    metrics: [
      "kWh semanal",
      "litros de generador",
      "kg CO2e / kWh",
      "consumo por frente",
      "horas de uso energético",
      "consumo fuera de horario",
    ],
    evidence: [
      "Boletas eléctricas",
      "Registro de generador",
      "Medición de tablero",
      "Partes diarios",
      "Registro de consumo por frente",
    ],
    nextStep:
      "Separar los consumos eléctricos de red y generador para detectar desviaciones a tiempo, antes de que esta etapa aumente su impacto en las emisiones totales de la obra.",
  },
};

const stageOperationalDisplayNames = {
  "retiro de residuos": "Retiro de residuos",
  "excavacion y movimiento de tierra": "Excavación y movimiento de tierra",
};

const clampValue = (value, min = 0, max = 100) =>
  Math.min(max, Math.max(min, Number(value) || 0));

const getOperationalCategoryLabel = (category) =>
  operationalCategoryDisplayNames[category] || category || "Sin categoría";

function getCategoryAccentStyle(category) {
  switch (category) {
    case "Materiales":
      return "border-amber-300/70 bg-amber-50 shadow-[0_14px_28px_rgba(217,119,6,0.14)] ring-1 ring-amber-200/50";
    case "Residuos":
      return "border-emerald-300/70 bg-emerald-50 shadow-[0_14px_28px_rgba(16,185,129,0.14)] ring-1 ring-emerald-200/50";
    case "Maquinaria":
      return "border-slate-300/70 bg-slate-50 shadow-[0_14px_28px_rgba(71,85,105,0.14)] ring-1 ring-slate-200/50";
    case "Energia":
      return "border-sky-300/70 bg-sky-50 shadow-[0_14px_28px_rgba(14,165,233,0.14)] ring-1 ring-sky-200/50";
    case "Transporte":
      return "border-cyan-300/70 bg-cyan-50 shadow-[0_14px_28px_rgba(6,182,212,0.14)] ring-1 ring-cyan-200/50";
    case "Agua":
      return "border-blue-300/70 bg-blue-50 shadow-[0_14px_28px_rgba(59,130,246,0.14)] ring-1 ring-blue-200/50";
    default:
      return "border-zinc-300/70 bg-zinc-50 shadow-[0_14px_28px_rgba(113,113,122,0.14)] ring-1 ring-zinc-200/50";
  }
}

const getOperationalStageKey = (stage) => normalizeInsightText(stage).replace(/\s+/g, " ");

const getOperationalStageLabel = (stage) =>
  stageOperationalDisplayNames[getOperationalStageKey(stage)] || stage || "Sin etapa";

const getOperationalRelevance = ({
  emissions,
  pct,
  total,
  evidenceCoverage,
  environmentalLabel,
  potentialReduction,
}) => {
  const percentage = Number(pct || 0);
  const absoluteEmissions = Number(emissions || 0);
  const totalEmissions = Number(total || 0);
  const evidenceValue = Number(evidenceCoverage || 0);
  const reductionValue = Number(potentialReduction || 0);
  const isCriticalState = normalizeInsightText(environmentalLabel).includes("crit");

  let label = "Monitoreo / sin datos críticos";

  if (percentage > 50) {
    label = "Foco crítico";
  } else if (percentage >= 15) {
    label = "Alta relevancia";
  } else if (percentage >= 5) {
    label = "Relevancia media";
  } else if (percentage > 0) {
    label = "Control secundario";
  }

  const baseScore =
    percentage > 50 ? 88 : percentage >= 15 ? 66 : percentage >= 5 ? 40 : percentage > 0 ? 18 : 10;
  const volumeBonus =
    totalEmissions > 0 ? Math.min(8, Math.round((absoluteEmissions / totalEmissions) * 8)) : 0;
  const stateBonus = isCriticalState && percentage > 0 ? 4 : 0;
  const reductionBonus = reductionValue > 0 ? Math.min(5, Math.round(reductionValue / 10)) : 0;
  const evidenceBonus = evidenceValue > 50 ? 3 : evidenceValue > 0 ? 1 : -2;

  return {
    label,
    score: clampValue(baseScore + volumeBonus + stateBonus + reductionBonus + evidenceBonus),
    summary:
      label === "Foco crítico"
        ? "Intervenir ahora y ejecutar un piloto antes de escalar cambios."
        : label === "Alta relevancia"
          ? "Mantener como prioridad operativa con seguimiento semanal."
          : label === "Relevancia media"
            ? "Controlar de forma periódica y documentar desviaciones."
            : label === "Control secundario"
              ? "Monitorear sin perder trazabilidad operacional."
              : "Mantener monitoreo y depuración de datos.",
  };
};

const getStageOperationalRelevance = ({
  emissions,
  pct,
  total,
  evidenceCoverage,
  environmentalLabel,
  stageRank,
  potentialReduction,
}) => {
  const percentage = Number(pct || 0);
  const absoluteEmissions = Number(emissions || 0);
  const totalEmissions = Number(total || 0);
  const evidenceValue = Number(evidenceCoverage || 0);
  const reductionValue = Number(potentialReduction || 0);
  const isCriticalState = normalizeInsightText(environmentalLabel).includes("crit");
  const momentBonus = Math.max(0, 8 - Number(stageRank || 0) * 2);

  let label = "Monitoreo operativo";

  if (percentage > 40) {
    label = "Etapa crítica";
  } else if (percentage >= 15) {
    label = "Alta relevancia";
  } else if (percentage >= 5) {
    label = "Relevancia media";
  } else if (percentage >= 1) {
    label = "Control secundario";
  }

  const baseScore =
    percentage > 40 ? 92 : percentage >= 15 ? 70 : percentage >= 5 ? 44 : percentage >= 1 ? 24 : 12;
  const volumeBonus =
    totalEmissions > 0 ? Math.min(8, Math.round((absoluteEmissions / totalEmissions) * 8)) : 0;
  const stateBonus = isCriticalState && percentage > 0 ? 6 : 0;
  const evidenceBonus = evidenceValue > 50 ? 4 : evidenceValue > 0 ? 2 : -2;
  const reductionBonus = reductionValue > 0 ? Math.min(4, Math.round(reductionValue / 12)) : 0;

  return {
    label,
    score: clampValue(baseScore + volumeBonus + stateBonus + evidenceBonus + reductionBonus + momentBonus),
    summary:
      label === "Etapa crítica"
        ? "Intervenir de inmediato y validar la fase antes de avanzar a la siguiente partida."
        : label === "Alta relevancia"
          ? "Mantener como prioridad operativa y cerrar brechas antes del siguiente avance."
          : label === "Relevancia media"
            ? "Controlar la fase de forma periódica con evidencia de seguimiento."
            : label === "Control secundario"
              ? "Monitorear la etapa sin perder trazabilidad operacional."
              : "Mantener monitoreo y depuración de datos.",
  };
};

const worksiteReductionSteps = [
  {
    title: "Optimizar rutas de despacho y transporte",
    detail:
      "Planificar mejor los recorridos, evitar viajes vacíos, combinar cargas y priorizar rutas más cortas o con menos tráfico para reducir kilómetros recorridos y consumo de combustible.",
  },
  {
    title: "Mejorar eficiencia de maquinaria y camiones",
    detail:
      "Implementar mantención preventiva, utilizar neumáticos adecuados, mantener los motores correctamente calibrados y reducir el tiempo de ralentí­.",
  },
  {
    title: "Controlar conduccion y operacion",
    detail:
      "Capacitar operadores para reducir aceleraciones bruscas, tiempos muertos y uso ineficiente de la maquinaria.",
  },
  {
    title: "Renovar flota gradualmente",
    detail:
      "Cambiar camiones o maquinaria antigua por modelos mas eficientes.",
  },
  {
    title: "Usar combustibles de menor emision",
    detail:
      "Evaluar biodiesel, diesel renovable u otras mezclas compatibles segun disponibilidad y costo.",
  },
  {
    title: "Electrificar operaciones internas especificas",
    detail:
      "Priorizar gruas, equipos de patio, montacargas o vehiculos livianos cuando sea viable.",
  },
  {
    title: "Planificar mejor acopio y secuencia de obra",
    detail:
      "Acercar puntos de acopio, reducir movimientos internos y evitar traslados repetidos entre frentes.",
  },
  {
    title: "Medir litros por frente",
    detail:
      "Separar consumo por cosecha, despacho, transporte, maquinaria y vehiculos.",
  },
];

function App() {
  const [data, setData] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardEmissionKpis, setDashboardEmissionKpis] = useState(null);
  const [companyStatus, setCompanyStatus] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");
  const [ConstructoraCreateSignal, setConstructoraCreateSignal] = useState(0);
  const { loadingAuth, user } = useAuth();
  const { activeConstructora, activeConstructoraId, loadingConstructoras } = useConstructoraActiva();

  const handleSetActiveView = useCallback((view, options = {}) => {
    setActiveView(view);
    if (options.openCreateConstructora) {
      setConstructoraCreateSignal((currentSignal) => currentSignal + 1);
    }
  }, []);

  const applyDashboardData = useCallback((dashboardData) => {
    setData(dashboardData);
    setDashboardError("");
  }, []);

  const refreshInternalDashboard = useCallback(async () => {
    if (!activeConstructoraId) {
      setData(null);
      setDashboardEmissionKpis(null);
      setCompanyStatus(null);
      return null;
    }

    const [dashboardResult, estadoResult, emissionsResult] = await Promise.allSettled([
      getConstructoraDashboard(activeConstructoraId, { light: "1" }),
      getConstructoraEstado(activeConstructoraId),
      getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
    ]);

    if (dashboardResult.status === "fulfilled") {
      applyDashboardData(dashboardResult.value);
    }

    if (estadoResult.status === "fulfilled") {
      setCompanyStatus(estadoResult.value);
    }

    if (emissionsResult.status === "fulfilled") {
      setDashboardEmissionKpis(emissionsResult.value?.kpis || null);
    } else {
      setDashboardEmissionKpis(null);
    }

    if (dashboardResult.status === "rejected" && estadoResult.status === "rejected") {
      throw dashboardResult.reason || estadoResult.reason;
    }

    return dashboardResult.status === "fulfilled" ? dashboardResult.value : null;
  }, [activeConstructoraId, applyDashboardData]);

  useEffect(() => {
    if (activeView !== "dashboard" || !activeConstructoraId) {
      if (!activeConstructoraId) {
        window.setTimeout(() => {
          setData(null);
          setDashboardEmissionKpis(null);
          setCompanyStatus(null);
        }, 0);
      }

      return;
    }

    let isCancelled = false;
    let timeoutId;

    const loadDashboard = async () => {
      if (document.visibilityState === "hidden") {
        timeoutId = window.setTimeout(loadDashboard, DASHBOARD_REFRESH_INTERVAL_MS);
        return;
      }

      try {
        const [dashboardResult, estadoResult, emissionsResult] = await Promise.allSettled([
          getConstructoraDashboard(activeConstructoraId, { light: "1" }),
          getConstructoraEstado(activeConstructoraId),
          getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
        ]);

        if (!isCancelled) {
          if (dashboardResult.status === "fulfilled") {
            applyDashboardData(dashboardResult.value);
          }

          if (estadoResult.status === "fulfilled") {
            setCompanyStatus(estadoResult.value);
          }

          if (emissionsResult.status === "fulfilled") {
            setDashboardEmissionKpis(emissionsResult.value?.kpis || null);
          } else {
            setDashboardEmissionKpis(null);
          }

          if (dashboardResult.status === "rejected" && estadoResult.status === "rejected") {
            throw dashboardResult.reason || estadoResult.reason;
          }
        }
      } catch (error) {
        if (!isCancelled) {
          setDashboardError(
            error.response?.data?.error || "No se pudieron cargar los datos de la constructora activa."
          );
        }
      } finally {
        if (!isCancelled) {
          timeoutId = window.setTimeout(loadDashboard, DASHBOARD_REFRESH_INTERVAL_MS);
        }
      }
    };

    loadDashboard();

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [activeConstructoraId, activeView, applyDashboardData]);

  const handleExportReport = () => {
    window.print();
  };

  const dashboardTotalEmissions = Number(data?.total_emisiones || 0);
  const dashboardStoredCarbon = Number(data?.balance_ambiental_total || 0);
  const dashboardHasRows = Array.isArray(data?.datos) && data.datos.length > 0;

  const recommendedScenario = useMemo(() => {
    if (dashboardHasRows) {
      const optimized = optimizeScenario(data.datos || []);
      return {
        ...optimized,
        currentTotal: dashboardTotalEmissions,
        simulatedTotal: dashboardTotalEmissions * (1 - Number(optimized.reductionPct || 0) / 100),
      };
    }

    if (!dashboardTotalEmissions) {
      return null;
    }

    const estimatedReductionPct = 25;
    return {
      currentTotal: dashboardTotalEmissions,
      simulatedTotal: dashboardTotalEmissions * (1 - estimatedReductionPct / 100),
      reductionPct: estimatedReductionPct,
      dieselReduction: 0,
      electricityIncrease: 0,
      rows: [],
    };
  }, [dashboardHasRows, dashboardTotalEmissions, data]);

  if (loadingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-main)] text-[var(--text-main)]">
        Cargando sesion...
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  if (loadingConstructoras) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-main)] text-[var(--text-main)]">
        Cargando constructoras...
      </div>
    );
  }

  if (!activeConstructora && activeView === "emisiones") {
    return (
      <main className="flex min-h-screen flex-col bg-[var(--bg-main)] text-[var(--text-main)] lg:flex-row">
        <div className="hidden lg:block">
          <Sidebar
            activeView={activeView}
            onSetActiveView={handleSetActiveView}
            systemStatus={companyStatus}
          />
        </div>
        <section className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-12 overflow-y-auto">
          <EmisionesView onSetActiveView={handleSetActiveView} />
        </section>
      </main>
    );
  }

  if (!activeConstructora) {
      // Show the constructoras page and open the create modal so the user can create a company
      return (
        <div className="min-h-screen bg-[var(--bg-main)] p-6 text-[var(--text-main)] sm:p-10">
          <ConstructorasView onSetActiveView={handleSetActiveView} initialOpenCreate={true} />
        </div>
      );
    }

    if (!data) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[var(--bg-main)] text-[var(--text-main)]">
          {dashboardError || "Cargando tablero de constructora..."}
        </div>
      );
    }
const dashboardRows = Array.isArray(data?.datos) ? data.datos : [];

const emisionesPorConstructora = data?.emisiones_por_Constructora ?? {};
const emisionesPorActividad = data?.emisiones_por_fuente_emision ?? {};
const emisionesPorEtapa =
  data?.emisiones_por_etapa ?? data?.emisiones_por_unidad ?? {};

const registros_emision = Object.entries(emisionesPorActividad).map(
  ([fuente_emision, emisiones]) => ({
    fuente_emision,
    emisiones,
  })
);

const etapas = Object.entries(emisionesPorEtapa).map(
  ([unidad, emisiones]) => ({
    unidad,
    emisiones,
  })
);

const fuenteCritica = data?.fuente_critica || registros_emision[0]?.fuente_emision || "Sin datos";
const unidadCritica = data?.etapa_critica || etapas[0]?.unidad || "Sin datos";
const safeDashboardData = {
  ...data,
  datos: dashboardRows,
  emisiones_por_Constructora: emisionesPorConstructora,
  emisiones_por_fuente_emision: emisionesPorActividad,
  total_emisiones: data?.total_emisiones ?? 0,
};

const riskProfile = calculateRiskProfile(safeDashboardData, recommendedScenario);
const dieselReductionImpactKg = dashboardEmissionKpis
  ? Number(dashboardEmissionKpis.emisiones_totales || 0) *
    (Number(dashboardEmissionKpis.porcentaje_diesel || 0) / 100) *
    0.25
  : null;
const dieselReductionEquivalentKm =
  dieselReductionImpactKg != null ? dieselReductionImpactKg * 4 : null;

const validationSummary = {
  records: dashboardRows.length,
  errors: 0,
  registros: new Set(dashboardRows.map((row) => row.fuente_emision)).size,
};
const isDieselcriticalSource = String(fuenteCritica || "")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase()
  .includes("diesel");
const rowsWithCategories = dashboardRows.map((row) => ({
  ...row,
  categoria_visible: getConstructionCategoryLabel(row.categoria, row.fuente_emision),
}));
const totalEmissions = Number(safeDashboardData.total_emisiones || 0);
const emissionsByWork = Object.values(
  rowsWithCategories.reduce((accumulator, row) => {
    const workCode = row.codigo_obra || row.obra || "Sin obra";
    const current = accumulator[workCode] || {
      name: workCode,
      emissions: 0,
      surface: Number(row.superficie_m2 || row.superficie || 0),
      records: 0,
    };

    current.emissions += Number(row.emisiones || row.emisiones_kg_co2e || 0);
    current.records += 1;
    if (!current.surface) {
      current.surface = Number(row.superficie_m2 || row.superficie || 0);
    }
    accumulator[workCode] = current;
    return accumulator;
  }, {})
).sort((left, right) => right.emissions - left.emissions);
const criticalWork = emissionsByWork[0]?.name || "Sin datos";
const totalDeclaredSurface = emissionsByWork.reduce(
  (total, work) => total + Number(work.surface || 0),
  0
);
const carbonIntensity =
  totalDeclaredSurface > 0 ? totalEmissions / totalDeclaredSurface : null;
const categoryDistribution = constructionCategories
  .map((category) => {
    const emissions = rowsWithCategories.reduce(
      (total, row) =>
        row.categoria_visible === category
          ? total + Number(row.emisiones || row.emisiones_kg_co2e || 0)
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
const criticalCategory = categoryDistribution.find((item) => item.emissions > 0)?.category || "Sin datos";
const emissionsByStage = Object.values(
  rowsWithCategories.reduce((accumulator, row) => {
    const stage = row.etapa_nombre || row.etapa || "Sin etapa";
    const current = accumulator[stage] || { stage, emissions: 0, records: 0 };
    current.emissions += Number(row.emisiones || row.emisiones_kg_co2e || 0);
    current.records += 1;
    accumulator[stage] = current;
    return accumulator;
  }, {})
).sort((left, right) => right.emissions - left.emissions);
const environmentalStatus = getEnvironmentalStatus({
  categoryDistribution,
  evidenceBacked: null,
  rows: rowsWithCategories,
  totalEmissions,
});

  return (
    <main className="flex min-h-screen flex-col bg-[var(--bg-main)] text-[var(--text-main)] lg:flex-row">
      <button
        type="button"
        onClick={() => setMobileMenuOpen(true)}
        className="fixed right-4 top-4 z-50 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)]/95 p-3 text-[var(--text-main)] shadow-[var(--shadow-card)] backdrop-blur lg:hidden"
      >
        <Menu size={22} />
      </button>

      {user?.is_demo && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-xs font-bold uppercase tracking-wide text-amber-100 shadow-xl backdrop-blur">
          Modo demo: solo lectura
        </div>
      )}

      <div className="hidden lg:block">
        <Sidebar
          activeView={activeView}
          onSetActiveView={handleSetActiveView}
          systemStatus={companyStatus}
        />
      </div>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            className="fixed inset-0 z-50 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
          <motion.div
            className="absolute inset-0 bg-slate-950/30 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          <motion.div
            className="absolute right-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-l border-white/10 bg-[var(--sidebar)] shadow-2xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          >
            <button
              type="button"
              onClick={() => setMobileMenuOpen(false)}
              className="absolute right-4 top-4 rounded-2xl border border-white/10 bg-white/10 p-3 text-slate-200"
            >
              <X size={20} />
            </button>

            <Sidebar
              activeView={activeView}
              onSetActiveView={(view, options) => {
                handleSetActiveView(view, options);
                setMobileMenuOpen(false);
              }}
              systemStatus={companyStatus}
            />
          </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-12 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={`${activeView}-${activeConstructoraId}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={viewTransition}
          >
        {activeView === "obras" ? (
          <ObrasView />
        ) : activeView === "constructoras" ? (
          <ConstructorasView
            onSetActiveView={handleSetActiveView}
            openCreateSignal={ConstructoraCreateSignal}
          />
        ) : activeView === "etapas" ? (
          <EtapasObraView />
        ) : activeView === "reportes" ? (
          <ReportesView 
              activeConstructoraId={activeConstructoraId}
              activeConstructora={activeConstructora}
          />
        ) : activeView === "emisiones" ? (
          <EmisionesView onSetActiveView={handleSetActiveView} />
        ) : activeView === "factores" ? (
          <FactoresView />
        ) : activeView === "evidencias" ? (
          <EvidenciasPage />
        ) : activeView === "usuarios" ? (
          <UsuariosPage />
        ) : activeView === "configuracion" ? (
          <ConfiguracionPage />
        ) : activeView === "importaciones" ? (
          <ImportacionesView onImportConfirmed={refreshInternalDashboard} />
        ) : (

        <div className="stagger-in max-w-7xl mx-auto space-y-6 sm:space-y-8">
          <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl border border-emerald-200/80 bg-[linear-gradient(180deg,rgba(236,253,243,1),rgba(209,250,229,0.9))] p-3 shadow-[0_14px_30px_rgba(14,124,102,0.14)] ring-1 ring-white/70">
                <Database className="text-[var(--primary-dark)]" />
              </div>
              <div>
                <h1 className="text-3xl font-black tracking-tight sm:text-4xl">
                  Carbono Zero
                </h1>
                <p className="text-[var(--text-muted)]">
                  Convierte datos reales de obra en medición, trazabilidad y decisiones para reducir emisiones durante la ejecución del proyecto.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleExportReport}
              className="premium-button-primary inline-flex w-full items-center justify-center rounded-2xl px-5 py-3 text-sm font-bold shadow-[0_16px_32px_rgba(14,124,102,0.22)] sm:w-fit"
            >
              Exportar reporte
            </button>
          </header>

          <ExecutiveSummary
            fuenteCritica={fuenteCritica}
            unidadCritica={unidadCritica}
            optimizedScenario={recommendedScenario}
            reductionEquivalentKm={dieselReductionEquivalentKm}
            riskProfile={riskProfile}
            validationSummary={validationSummary}
          />

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-3">
            <KpiCard
              icon={<Activity />}
              title="Emisiones totales"
              value={`${formatNumber(totalEmissions)} kg CO2e`}
            />
            <KpiCard
              icon={<Factory />}
              title="Obra critica"
              value={criticalWork}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Categoría critica"
              value={criticalCategory}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Fuente critica"
              value={fuenteCritica}
            />
            <KpiCard
              icon={<Database />}
              title="Evidencia respaldada"
              value="Pendiente de vinculación"
            />
            <KpiCard
              icon={<Factory />}
              title="Intensidad de carbono"
              value={
                carbonIntensity != null
                  ? `${formatNumber(carbonIntensity, 2)} kg CO2e/m²`
                  : "Pendiente de superficie"
              }
            />
          </section>

          <OperationalIntelligenceModule
            data={safeDashboardData}
            items={categoryDistribution}
            total={totalEmissions}
            environmentalStatus={environmentalStatus}
            riskProfile={riskProfile}
          />

          <section className="grid grid-cols-1 gap-4">
            <StageOperationalModule
              data={safeDashboardData}
              items={emissionsByStage}
              total={totalEmissions}
              environmentalStatus={environmentalStatus}
              riskProfile={riskProfile}
            />
          </section>

          <CriticalDriversPanel
            categoryItems={categoryDistribution}
            stageItems={emissionsByStage}
            total={totalEmissions}
          />

          <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />

          {isDieselcriticalSource && (
            <section className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/40 sm:p-6">
              <div className="mb-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Pasos a seguir
                </p>
                <h2 className="mt-1 text-xl font-bold text-[var(--text-main)]">
                  Como reducir emisiones dentro de la operación.
                </h2>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {worksiteReductionSteps.map((step, index) => (
                  <div
                    key={step.title}
                    className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-4"
                  >
                    <p className="text-xs font-bold text-[var(--primary-dark)]">
                      Paso {index + 1}
                    </p>
                    <h3 className="mt-2 text-sm font-bold text-[var(--text-main)]">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                      {step.detail}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
        )}
          </motion.div>
        </AnimatePresence>
      </section>
    </main>
  );
}

export default App;

function getEnvironmentalStatus({ categoryDistribution, evidenceBacked, rows, totalEmissions }) {
  if (!rows.length || !totalEmissions) {
    return {
      label: "Sin datos",
      detail: "Aún no hay registros suficientes.",
      className: "border-slate-300 bg-slate-100 text-slate-700",
    };
  }

  const maxShare = Math.max(...categoryDistribution.map((item) => item.pct || 0), 0);
  const activeCategories = categoryDistribution.filter((item) => item.emissions > 0).length;

  if (evidenceBacked != null && evidenceBacked >= 50 && maxShare <= 50) {
    return {
      label: "Controlada",
      detail: "Sin concentración dominante y con documentación suficiente.",
      className: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    };
  }

  if (maxShare > 60) {
    return {
      label: "Crítica",
      detail: "Una categoría concentra más del 60% de las emisiones.",
      className: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
    };
  }

  if (activeCategories >= 3) {
    return {
      label: "En seguimiento",
      detail: "Existen registros distribuidos en varias categorías.",
      className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    };
  }

  return {
    label: "Inicial",
    detail: "Existen registros, pero aún falta trazabilidad por categoría.",
    className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
  };
}

const normalizeInsightText = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

function buildDocumentationNote(requiredItems = [], evidenceCoverage = 0, metrics = []) {
  const coverage = Number(evidenceCoverage || 0);
  const referenceItems = requiredItems.slice(0, 3);
  const referenceMetrics = metrics.slice(0, 2);
  const metricClause = referenceMetrics.length ? ` El sistema valida internamente ${referenceMetrics.join(", ")}.` : "";

  if (!referenceItems.length) {
    return {
      label: "Sin requerimientos documentales",
      text: "El sistema puede procesar la información con la evidencia disponible.",
    };
  }

  if (coverage >= 80) {
    return {
      label: "Diagnóstico respaldado",
      text: `La evidencia disponible permite sostener la lectura operativa con ${referenceItems.join(", ")}.${metricClause}`,
    };
  }

  if (coverage >= 50) {
    return {
      label: "Respaldo parcial",
      text: `El sistema aún debe contrastar ${referenceItems.join(", ")} para cerrar el diagnóstico.${metricClause}`,
    };
  }

  return {
    label: "Falta documentación",
    text: `El sistema no puede emitir un diagnóstico claro. Falta: ${referenceItems.join(", ")}.${metricClause}`,
  };
}

function OperationalIntelligenceModule({ data, items, total, environmentalStatus, riskProfile }) {
  const orderedItems = useMemo(() => {
    const itemMap = new Map(items.map((item) => [item.category, item]));

    return operationalCategoryOrder.map((category) => {
      const item = itemMap.get(category);

      return (
        item || {
          category,
          emissions: 0,
          pct: 0,
        }
      );
    });
  }, [items]);

  const defaultCategory = useMemo(() => {
    const topItem = orderedItems.reduce((best, item) => {
      if (!best) {
        return item;
      }

      if ((item.pct || 0) > (best.pct || 0)) {
        return item;
      }

      if ((item.pct || 0) === (best.pct || 0) && (item.emissions || 0) > (best.emissions || 0)) {
        return item;
      }

      return best;
    }, null);

    return topItem?.category || "Materiales";
  }, [orderedItems]);

  const [selectedCategory, setSelectedCategory] = useState(defaultCategory);

  useEffect(() => {
    setSelectedCategory((currentCategory) =>
      orderedItems.some((item) => item.category === currentCategory)
        ? currentCategory
        : defaultCategory
    );
  }, [defaultCategory, orderedItems]);

  const selectedItem =
    orderedItems.find((item) => item.category === selectedCategory) ||
    orderedItems[0] || {
      category: "Materiales",
      emissions: 0,
      pct: 0,
    };

  const selectedCopy = operationalIntelligence[selectedItem.category] || operationalIntelligence.Otros;
  const documentationNote = buildDocumentationNote(
    selectedCopy.evidence,
    data?.evidencia_respaldada || 0,
    selectedCopy.metrics
  );

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <p className="text-xs font-black uppercase tracking-[0.28em] text-[var(--text-muted)]">
            Inteligencia operativa
          </p>
          <h2 className="text-2xl font-black tracking-tight text-[var(--text-main)] sm:text-3xl">
            Módulo integrado de decisión ambiental
          </h2>
          <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)] sm:text-[15px]">
            Selecciona una categoría para interpretar su impacto, priorizar acciones, validar evidencia y definir el siguiente paso operativo.
          </p>
        </div>

        <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${environmentalStatus.className}`}>
          <p className="text-xs uppercase tracking-wide opacity-80">Estado ambiental general</p>
          <p className="mt-1 text-lg">{environmentalStatus.label}</p>
          <p className="mt-1 max-w-xs text-sm font-medium opacity-85">{environmentalStatus.detail}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[28px] border border-[color-mix(in_srgb,var(--primary)_16%,white)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-5 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-6">
          <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex-1 space-y-2 text-center sm:pr-6 sm:text-left">
              <div>
                <h3 className="text-2xl font-black tracking-tight text-[var(--text-main)]">
                  {getOperationalCategoryLabel(selectedItem.category)}
                </h3>
                <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                  {selectedCopy.relevanceLabel}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Emisiones de la categoría
              </p>
              <p className="mt-1 text-3xl font-black text-[var(--text-main)]">
                {formatNumber(selectedItem.emissions, 1)} kg CO2e
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                {formatNumber(selectedItem.pct || 0, 1)}% del total
              </p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)] sm:col-span-2">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Diagnóstico operativo
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
                {selectedCopy.diagnosis}
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Acciones recomendadas
            </p>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.actions.map((action) => (
                <li key={action} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-100/80 p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Documentación requerida
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {documentationNote.label}: {documentationNote.text}
            </p>
          </div>

          <div className="mt-5 rounded-2xl border border-[color-mix(in_srgb,var(--primary)_18%,white)] bg-[linear-gradient(180deg,rgba(236,253,245,0.9),rgba(255,255,255,0.98))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--primary-dark)]">
              Siguiente paso recomendado
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.nextStep}
            </p>
          </div>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
          <div className="border-b border-[var(--border)] pb-4">
            <p className="whitespace-nowrap text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)] sm:text-[11px]">
              Emisiones por categoría
            </p>
            <h3 className="mt-2 text-xl font-black text-[var(--text-main)]">
              Fuente de datos interactiva
            </h3>
            <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-[var(--text-muted)]">
              Selecciona una categoría para actualizar la inteligencia.
            </p>
          </div>

          <div className="mt-4 space-y-3">
            {orderedItems.map((item) => (
              <MetricBar
                key={item.category}
                label={getOperationalCategoryLabel(item.category)}
                pct={item.pct}
                value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                detail={
                  item.category === selectedItem.category
                    ? "Foco actual"
                    : item.pct > 0
                      ? "Disponible para intervención"
                      : "Monitoreo sin emisiones"
                }
                activeClassName={getCategoryAccentStyle(item.category)}
                isActive={item.category === selectedItem.category}
                onClick={() => setSelectedCategory(item.category)}
              />
            ))}

            {!total && (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4 text-sm text-[var(--text-muted)]">
                No hay registros de emision suficientes.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function StageOperationalModule({ data, items, total, environmentalStatus, riskProfile }) {
  const orderedItems = useMemo(() => {
    const itemMap = new Map(items.map((item) => [getOperationalStageKey(item.stage), item]));

    const orderedStages = stageOperationalOrder.map((stage) => {
      const item = itemMap.get(getOperationalStageKey(stage));

      return (
        item || {
          stage,
          emissions: 0,
          records: 0,
        }
      );
    });

    const knownStageKeys = new Set(orderedStages.map((item) => getOperationalStageKey(item.stage)));
    const extraStages = items.filter((item) => !knownStageKeys.has(getOperationalStageKey(item.stage)));

    return [...orderedStages, ...extraStages];
  }, [items]);

  const defaultStage = useMemo(() => {
    const topItem = orderedItems.reduce((best, item) => {
      if (!best) {
        return item;
      }

      if ((item.emissions || 0) > (best.emissions || 0)) {
        return item;
      }

      return best;
    }, null);

    return getOperationalStageKey(topItem?.stage || stageOperationalOrder[0]);
  }, [orderedItems]);

  const [selectedStage, setSelectedStage] = useState(defaultStage);

  useEffect(() => {
    setSelectedStage((currentStage) =>
      orderedItems.some((item) => getOperationalStageKey(item.stage) === currentStage)
        ? currentStage
        : defaultStage
    );
  }, [defaultStage, orderedItems]);

  const selectedItem =
    orderedItems.find((item) => getOperationalStageKey(item.stage) === selectedStage) ||
    orderedItems[0] || {
      stage: stageOperationalOrder[0],
      emissions: 0,
      records: 0,
    };

  const selectedKey = getOperationalStageKey(selectedItem.stage);
  const selectedCopy = stageOperationalIntelligence[selectedKey] || stageOperationalIntelligence["fundaciones"];
  const documentationNote = buildDocumentationNote(
    selectedCopy.evidence,
    data?.evidencia_respaldada || 0,
    selectedCopy.metrics
  );
  const stageRank = Math.max(
    0,
    stageOperationalOrder.findIndex((stage) => getOperationalStageKey(stage) === selectedKey)
  );
  const relevance = getStageOperationalRelevance({
    emissions: selectedItem.emissions,
    pct: total > 0 ? (selectedItem.emissions / total) * 100 : 0,
    total,
    evidenceCoverage: data?.evidencia_respaldada || 0,
    environmentalLabel: environmentalStatus.label,
    stageRank,
    potentialReduction: riskProfile?.factors?.potentialReduction || 0,
  });

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <p className="text-xs font-black uppercase tracking-[0.28em] text-[var(--text-muted)]">
            Inteligencia por etapa
          </p>
          <h2 className="text-2xl font-black tracking-tight text-[var(--text-main)] sm:text-3xl">
            Módulo operativo por fase de obra
          </h2>
          <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)] sm:text-[15px]">
            Selecciona una etapa para interpretar su impacto, priorizar acciones, validar evidencia y decidir el siguiente avance de la obra.
          </p>
        </div>

        <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${environmentalStatus.className}`}>
          <p className="text-xs uppercase tracking-wide opacity-80">Estado operativo general</p>
          <p className="mt-1 text-lg">{environmentalStatus.label}</p>
          <p className="mt-1 max-w-xs text-sm font-medium opacity-85">{environmentalStatus.detail}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[28px] border border-[color-mix(in_srgb,var(--primary)_16%,white)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-5 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-6">
          <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex-1 space-y-2 text-center sm:pr-6 sm:text-left">
              <div>
                <h3 className="text-2xl font-black tracking-tight text-[var(--text-main)]">
                  {getOperationalStageLabel(selectedItem.stage)}
                </h3>
                <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                  {selectedCopy.relevanceLabel}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Emisiones de la etapa
              </p>
              <p className="mt-1 text-3xl font-black text-[var(--text-main)]">
                {formatNumber(selectedItem.emissions, 1)} kg CO2e
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                {formatNumber(total > 0 ? (selectedItem.emissions / total) * 100 : 0, 1)}% del total
              </p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)] sm:col-span-2">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Diagnóstico de la fase
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
                {selectedCopy.diagnosis}
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Acciones recomendadas
            </p>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.actions.map((action) => (
                <li key={action} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-100/80 p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Documentación requerida
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {documentationNote.label}: {documentationNote.text}
            </p>
          </div>

          <div className="mt-5 rounded-2xl border border-[color-mix(in_srgb,var(--primary)_18%,white)] bg-[linear-gradient(180deg,rgba(236,253,245,0.9),rgba(255,255,255,0.98))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--primary-dark)]">
              Siguiente paso recomendado
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.nextStep}
            </p>
          </div>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
          <div className="border-b border-[var(--border)] pb-4">
            <p className="whitespace-nowrap text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)] sm:text-[11px]">
              Impacto de emisiones por etapa de obra
            </p>
            <h3 className="mt-2 text-xl font-black text-[var(--text-main)]">
              Análisis interactivo por etapa
            </h3>
            <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-[var(--text-muted)]">
              Selecciona una etapa para visualizar su diagnóstico operativo, nivel de impacto y recomendaciones específicas.
            </p>
          </div>

          <div className="mt-4 space-y-3">
            {orderedItems.map((item, index) => (
              <MetricBar
                key={item.stage}
                label={getOperationalStageLabel(item.stage)}
                pct={total > 0 ? (item.emissions / total) * 100 : 0}
                value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                detail={
                  item.stage === selectedItem.stage
                    ? "Etapa seleccionada"
                    : item.emissions > 0
                      ? (
                        item.stage === "fundaciones"
                          ? "Mayor prioridad de intervención"
                          : item.stage === "obra gruesa"
                            ? "Segunda prioridad de intervención"
                            : item.stage === "terminaciones"
                              ? "Impacto medio dentro de la obra"
                              : item.stage === "retiro de residuos"
                                ? "Impacto bajo, mantener control documental"
                                : item.stage === "excavacion y movimiento de tierra"
                                  ? "Impacto bajo, revisar uso de maquinaria"
                                  : `Etapa ${index + 1} de intervención`
                      )
                      : "Monitoreo sin emisiones"
                }
                badge={item.stage === selectedItem.stage ? "SELECCIONADA" : null}
                isActive={item.stage === selectedItem.stage}
                onClick={() => setSelectedStage(getOperationalStageKey(item.stage))}
              />
            ))}

            {!total && (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4 text-sm text-[var(--text-muted)]">
                Aún no hay etapas o frentes asociados a los registros.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function CriticalDriversPanel({ categoryItems, stageItems, total }) {
  const topCategories = categoryItems.slice(0, 3);
  const topStages = stageItems.slice(0, 3);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-[var(--text-muted)]">
            Fuentes críticas
          </p>
          <h2 className="mt-1 text-2xl font-black tracking-tight text-[var(--text-main)]">
            Top 3 de mayor impacto
          </h2>
        </div>
        <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
          El sistema prioriza las tres categorías y las tres etapas con mayor impacto para orientar la lectura ejecutiva.
        </p>
      </div>

      <div className="mt-5 space-y-5">
        <div className="rounded-[28px] border border-[var(--border)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
                Top 3 por categorías
              </p>
              <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">
                Categorías con mayor huella
              </h3>
            </div>
            <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-3 py-1 text-[11px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
              {topCategories.length} KPI
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            {topCategories.length ? (
              topCategories.map((item, index) => (
                <CriticalKpiCard
                  key={item.category}
                  accent={index}
                  label={getOperationalCategoryLabel(item.category)}
                  value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                  percent={total > 0 ? (item.emissions / total) * 100 : 0}
                  rank={index + 1}
                />
              ))
            ) : (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-muted)] lg:col-span-3">
                No hay registros de emision suficientes.
              </p>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
                Top 3 por etapas
              </p>
              <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">
                Fases con mayor impacto
              </h3>
            </div>
            <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-3 py-1 text-[11px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
              {topStages.length} KPI
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            {topStages.length ? (
              topStages.map((item, index) => (
                <CriticalKpiCard
                  key={item.stage}
                  accent={index}
                  label={getOperationalStageLabel(item.stage)}
                  value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                  percent={total > 0 ? (item.emissions / total) * 100 : 0}
                  rank={index + 1}
                />
              ))
            ) : (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-muted)] lg:col-span-3">
                Aún no hay etapas o frentes asociados a los registros.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function CriticalKpiCard({ accent = 0, label, percent, rank, value }) {
  const accentClasses = [
    "from-emerald-50 via-white to-white ring-emerald-200/50",
    "from-cyan-50 via-white to-white ring-cyan-200/50",
    "from-amber-50 via-white to-white ring-amber-200/50",
  ];

  const accentClass = accentClasses[accent] || accentClasses[0];

  return (
    <article className={`relative overflow-hidden rounded-[24px] border bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.05)] ring-1 ${accentClass}`}>
      <div className="flex items-start justify-between gap-3">
        <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--primary-dark)]">
          Top {rank}
        </span>
        <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">
          {formatNumber(percent || 0, 1)}%
        </span>
      </div>

      <div className="mt-5 flex min-h-[132px] flex-col items-center justify-center text-center">
        <p className="text-sm font-bold uppercase tracking-[0.16em] text-[var(--text-muted)]">
          {label}
        </p>
        <p className="mt-3 text-3xl font-black tracking-tight text-[var(--text-main)]">
          {value}
        </p>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-[var(--primary)]"
          style={{ width: `${Math.max(4, Math.min(100, percent || 0))}%` }}
        />
      </div>

      <p className="mt-3 text-center text-xs font-semibold text-[var(--text-muted)]">
        Impacto sobre la empresa: {formatNumber(percent || 0, 1)}%
      </p>
    </article>
  );
}

function MetricBar({ activeClassName, badge, detail, isActive, label, onClick, pct, value }) {
  const Component = onClick ? "button" : "div";

  return (
    <Component
      type={onClick ? "button" : undefined}
      onClick={onClick}
      aria-pressed={onClick ? Boolean(isActive) : undefined}
      className={`premium-card-interactive w-full rounded-2xl border p-4 text-left ${
        onClick ? "cursor-pointer" : ""
      } ${
        isActive
          ? activeClassName || "border-[var(--primary)]/45 bg-[var(--success-bg)] shadow-[0_14px_28px_rgba(14,124,102,0.14)] ring-1 ring-[var(--primary)]/15"
          : "border-[var(--border)] bg-[var(--bg-card)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-[var(--text-main)]">{label}</p>
            {badge && (
              <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
                {badge}
              </span>
            )}
          </div>
          {detail && <p className="mt-1 text-xs text-[var(--text-muted)]">{detail}</p>}
        </div>
        <div className="text-right">
          <p className="font-bold text-[#075985]">{value}</p>
          <p className="text-xs text-[var(--text-muted)]">{formatNumber(pct || 0, 1)}%</p>
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full ${
            isActive ? "bg-[var(--primary-dark)]" : "bg-[var(--primary)]"
          }`}
          style={{ width: `${Math.max(0, Math.min(100, pct || 0))}%` }}
        />
      </div>
    </Component>
  );
}
