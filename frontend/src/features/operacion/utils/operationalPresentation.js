const normalize = (value) => String(value || "")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase();

const reasonText = (value) => normalize(
  Array.isArray(value?.motivos) ? value.motivos.join(" ") : value,
);

const includesAny = (text, terms) => terms.some((term) => text.includes(term));

const review = (message) => ({
  label: "Requiere revisión",
  tone: "warning",
  message,
});

export function eligibilityPresentation(eligibility) {
  if (["calculable_completo", "calculable_incompleto"].includes(eligibility?.estado)) {
    return {
      label: "Listo para evaluación",
      tone: "success",
      message: "Metodología y factor disponibles.",
    };
  }

  const text = reasonText(eligibility);
  if (includesAny(text, ["fallo tecnico", "fallo técnico", "procesamiento del respaldo", "revision tecnica"])) {
    return review("El respaldo no pudo procesarse. Puedes revisarlo o reintentarlo.");
  }
  if (includesAny(text, ["evidencia historica tiene observaciones", "respaldo tiene observaciones", "evidencia observada"])) {
    return review("El respaldo tiene observaciones pendientes de revisión.");
  }
  if (includesAny(text, ["contradic", "diferencias con el dato"])) {
    return review("El respaldo presenta diferencias con el dato registrado.");
  }
  if (text.includes("anterior al inicio de la obra")) {
    return review("La fecha del registro es anterior al inicio de la obra.");
  }
  if (eligibility?.estado === "requiere_revision") {
    return review("La información necesita revisión antes de calcular.");
  }
  if (eligibility?.metodologia_candidata) {
    return review("Revisa el dato o respaldo indicado antes de calcular.");
  }
  return {
    label: "No elegible",
    tone: "neutral",
    message: "No hay una metodología calculable para este registro.",
  };
}

function documentaryState(item) {
  const evidence = item?.observacion_detalle?.evidencia;
  return normalize(
    evidence?.validacion_documental?.estado
    || item?.dimensiones?.respaldo_documental
    || evidence?.estado_documental,
  );
}

export function qualityPresentation(item) {
  const evidence = item?.observacion_detalle?.evidencia;
  const documentary = documentaryState(item);
  const text = `${documentary} ${reasonText(item)}`;

  if (includesAny(text, ["revision_tecnica", "fallo tecnico", "procesamiento documental presento un fallo", "estado_procesamiento error"])) {
    return review("El respaldo no pudo procesarse.");
  }
  if (text.includes("contradic")) {
    return review("El respaldo presenta diferencias con el dato registrado.");
  }
  if (text.includes("no_pertinente")) {
    return review("El archivo adjunto no corresponde al respaldo esperado.");
  }
  if (text.includes("compatible_incompleta")) {
    return review("El respaldo es compatible, pero está incompleto.");
  }
  if (includesAny(text, ["observada", "tiene observaciones"])) {
    return review("El respaldo tiene observaciones pendientes.");
  }
  if (item?.estado === "confiable") {
    return { label: "Confiable", tone: "success", message: "Dato verificado y utilizable." };
  }
  if (item?.estado === "confiable_con_observaciones") {
    return {
      label: "Confiable con observaciones",
      tone: "warning",
      message: evidence
        ? "Respaldo adjunto, pendiente de validación."
        : "Dato manual sin respaldo documental.",
    };
  }
  if (item?.estado === "no_confiable") {
    return {
      label: "No confiable",
      tone: "danger",
      message: "El dato no cumple las condiciones para ser utilizado.",
    };
  }
  return review("El dato necesita revisión antes de utilizarse.");
}

export function evidencePresentation(evidence) {
  if (!evidence) return { label: "Sin evidencia", tone: "neutral", message: "Sin evidencia" };
  const state = normalize(
    evidence.validacion_documental?.estado || evidence.estado_documental,
  );
  const labels = {
    verificada: "Verificado",
    validada: "Verificado",
    compatible_incompleta: "En revisión",
    indeterminada: "En revisión",
    pendiente: "En revisión",
    pendiente_procesamiento: "Procesando",
    recibida: "Procesando",
    analizando: "Procesando",
    observada: "Observado",
    contradiccion: "Contradice el dato",
    no_pertinente: "No pertinente",
    revision_tecnica: "En revisión",
    error: "En revisión",
  };
  return {
    label: labels[state] || "En revisión",
    tone: "neutral",
    message: labels[state] || "En revisión",
  };
}
