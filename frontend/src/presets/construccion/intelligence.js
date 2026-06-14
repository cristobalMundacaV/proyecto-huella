import { getConstructionCategoryLabel } from "@/features/obras/utils/constructionEmissionCategories";

const categoryOrder = [
  "Materiales",
  "Residuos",
  "Maquinaria",
  "Energia",
  "Transporte",
  "Agua",
  "Otros",
];

const categoryDisplayNames = {
  Energia: "Energía",
};

const categoryIntelligence = {
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

const stageOrder = [
  "Fundaciones",
  "Obra gruesa",
  "Terminaciones",
  "Retiro de residuos",
  "Excavación y movimiento de tierra",
  "Instalaciones",
];

const stageIntelligence = {
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

const stageDisplayNames = {
  "retiro de residuos": "Retiro de residuos",
  "excavacion y movimiento de tierra": "Excavación y movimiento de tierra",
};

const resolveCategoryLabel = getConstructionCategoryLabel;

const normalizeInsightText = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

const clampValue = (value, min = 0, max = 100) =>
  Math.min(max, Math.max(min, Number(value) || 0));

const getOperationalCategoryLabel = (category) =>
  categoryDisplayNames[category] || category || "Sin categoría";

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
  stageDisplayNames[getOperationalStageKey(stage)] || stage || "Sin etapa";

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

const reductionSteps = [
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

const constructionIntelligence = {
  categoryOrder,
  categoryDisplayNames,
  categoryIntelligence,
  stageOrder,
  stageDisplayNames,
  stageIntelligence,
  reductionSteps,
  resolveCategoryLabel,
  getOperationalCategoryLabel,
  getCategoryAccentStyle,
  getOperationalStageKey,
  getOperationalStageLabel,
  getStageOperationalRelevance,
};

export {
  categoryOrder,
  categoryDisplayNames,
  categoryIntelligence,
  stageOrder,
  stageDisplayNames,
  stageIntelligence,
  reductionSteps,
  constructionIntelligence,
  resolveCategoryLabel,
  clampValue,
  getOperationalCategoryLabel,
  getCategoryAccentStyle,
  getOperationalStageKey,
  getOperationalStageLabel,
  getOperationalRelevance,
  getStageOperationalRelevance,
};
