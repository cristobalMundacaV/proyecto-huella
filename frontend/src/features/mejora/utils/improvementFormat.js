const PROBLEM_STATES = {
  detectada: { label: "Detectado", tone: "warning" },
  analizando: { label: "En análisis", tone: "warning" },
  propuesta: { label: "Con alternativas", tone: "info" },
  accion_seleccionada: { label: "Acción seleccionada", tone: "info" },
  implementando: { label: "En implementación", tone: "info" },
  seguimiento: { label: "En seguimiento", tone: "info" },
  evaluando: { label: "Evaluando resultado", tone: "info" },
  escalada_profesional: { label: "Revisión profesional", tone: "warning" },
  cerrada: { label: "Cerrado", tone: "success" },
  en_analisis: { label: "En análisis", tone: "warning" },
  accion_propuesta: { label: "Con alternativas", tone: "info" },
  en_implementacion: { label: "En implementación", tone: "info" },
  en_seguimiento: { label: "En seguimiento", tone: "info" },
  resuelta: { label: "Resuelto", tone: "success" },
  mejora_insuficiente: { label: "Resultado insuficiente", tone: "warning" },
  no_resuelta: { label: "No resuelto", tone: "danger" },
  escalada: { label: "Revisión requerida", tone: "warning" },
};


const ACTION_STATES = {
  propuesta: "Propuesta",
  ajustada: "Ajustada",
  seleccionada: "Seleccionada",
  en_implementacion: "En implementación",
  seguimiento: "En seguimiento",
  implementada: "Implementada",
  evaluada: "Evaluada",
  descartada: "Descartada",
  cancelada: "Cancelada",
};

const RISK_LABELS = { bajo: "Bajo", medio: "Medio", alto: "Alto", critico: "Crítico" };

const RESULT_LABELS = {
  efectiva: "Efectiva",
  parcialmente_efectiva: "Parcialmente efectiva",
  no_efectiva: "No efectiva",
  no_implementada: "No implementada",
  no_viable: "No viable",
  parcial: "Parcial",
  implementada_sin_efecto: "Sin efecto demostrado",
  positiva: "Resultado positivo",
  negativa: "Resultado negativo",
  inconclusa: "Inconclusa",
};

export const label = (value) =>
  value === null || value === undefined || value === ""
    ? "Sin datos"
    : String(value).replaceAll("_", " ");

export const problemStatus = (state) =>
  PROBLEM_STATES[state] || { label: label(state), tone: "neutral" };

export const problemStatusLabel = (state) => problemStatus(state).label;

export const problemTone = (state) => problemStatus(state).tone;

export const actionStatusLabel = (state) => ACTION_STATES[state] || label(state);

export const riskLabel = (value) => RISK_LABELS[value] || "Sin datos";

export const resultLabel = (value) =>
  !value || value === "pendiente"
    ? "Aún sin evaluación"
    : RESULT_LABELS[value] || label(value);

export const currentAction = (actions = [], cycle = null) => {
  const active = actions.find((action) =>
    ["seleccionada", "en_implementacion", "seguimiento"].includes(action.estado),
  );
  if (active) return active;
  if (cycle?.accion) {
    return actions.find((action) => String(action.id) === String(cycle.accion)) || null;
  }
  return null;
};

export const currentCycle = (cycles = []) =>
  cycles.length ? [...cycles].sort((a, b) => Number(b.numero) - Number(a.numero))[0] : null;

export function problemNextStep({ problem, action, measurements = [], cycles = [] }) {
  const state = problem?.estado;
  if (["cerrada", "resuelta"].includes(state)) {
    return { type: "result", title: "Revisar resultado", description: "El ciclo ya cuenta con una evaluación registrada." };
  }
  if (["escalada_profesional", "escalada"].includes(state)) {
    return { type: "professional", title: "Seguir revisión profesional", description: "El problema está en una instancia de revisión especializada." };
  }
  const closedCycles = cycles.filter((cycle) => cycle.fecha_cierre).length;
  if (closedCycles >= 3 && ["no_resuelta", "mejora_insuficiente"].includes(state)) {
    return { type: "professional", title: "Solicitar revisión profesional", description: "Ya existen tres ciclos cerrados y el flujo permite escalar el problema." };
  }
  if (state === "accion_seleccionada" || action?.estado === "seleccionada") {
    return { type: "start", title: "Iniciar acción", description: "Confirma el inicio para congelar la situación BASE del ciclo." };
  }
  if (["implementando", "en_implementacion"].includes(state) || action?.estado === "en_implementacion") {
    return { type: "measurement", title: "Registrar seguimiento", description: "Incorpora una medición posterior para verificar lo que ocurrió después de la intervención." };
  }
  if (["seguimiento", "en_seguimiento"].includes(state)) {
    return measurements.length
      ? { type: "evaluate", title: "Evaluar resultado", description: "Ya existen mediciones de seguimiento para contrastar el resultado." }
      : { type: "measurement", title: "Agregar medición", description: "Se necesita seguimiento antes de evaluar el resultado." };
  }
  if (state === "evaluando") {
    return { type: "evaluate", title: "Evaluar resultado", description: "Revisa la información disponible y registra la evaluación cuando corresponda." };
  }
  if (["propuesta", "accion_propuesta", "mejora_insuficiente", "no_resuelta"].includes(state)) {
    return { type: "actions", title: "Revisar alternativas", description: "Compara las acciones propuestas y selecciona una antes de iniciar un nuevo ciclo." };
  }
  return { type: "review", title: "Revisar alcance e indicadores", description: "Confirma qué situación se intenta resolver y con qué indicador se verificará." };
}
