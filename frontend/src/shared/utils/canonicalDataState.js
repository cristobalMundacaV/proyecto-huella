export const canonicalDataStates = {
  captured: { label: "Capturado", tone: "info", description: "La información fue registrada y conserva su origen." },
  incomplete: { label: "Incompleto", tone: "warning", description: "Faltan antecedentes requeridos por el contrato actual." },
  ready: { label: "Listo para evaluación", tone: "success", description: "El backend confirmó que existe una metodología aplicable." },
  ineligible: { label: "No elegible", tone: "neutral", description: "El backend no encontró una metodología aplicable y calculable." },
  review: { label: "Requiere revisión", tone: "warning", description: "La información necesita una decisión o revisión humana." },
};

export function eligibilityStateInfo(eligibility) {
  const state = eligibility?.estado;
  if (state === "requiere_revision") return canonicalDataStates.review;
  if (["calculable_completo", "calculable_incompleto"].includes(state)) return canonicalDataStates.ready;
  if (["no_calculable", "no_aplicable"].includes(state)) return canonicalDataStates.ineligible;
  return canonicalDataStates.incomplete;
}

export function captureStateInfo(value) {
  if (["completado", "validada", "validado", "vinculada", "con_datos"].includes(value)) return canonicalDataStates.captured;
  if (["requiere_revision", "observada", "completado_con_observaciones"].includes(value)) return canonicalDataStates.review;
  return canonicalDataStates.incomplete;
}
