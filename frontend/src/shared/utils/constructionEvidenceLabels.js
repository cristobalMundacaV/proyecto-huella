const constructionEvidenceTypeOptions = [
  ["guia_despacho", "Guía de despacho"],
  ["factura_combustible", "Factura de combustible"],
  ["factura_electrica", "Boleta eléctrica"],
  ["boleta_electrica", "Boleta eléctrica"],
  ["certificado_origen", "Certificado de proveedor"],
  ["certificado_forestal", "Certificado de proveedor"],
  ["documento_transporte", "Documento de transporte"],
  ["ticket_pesaje", "Ticket de pesaje"],
  ["registro_gps", "Registro de maquinaria"],
  ["fotografia", "Registro fotográfico"],
  ["ficha_tecnica", "Ficha técnica de material"],
  ["otro", "Otro"],
];

const constructionWorkDocumentTypeOptions = [
  ["guia_despacho", "Guía de despacho"],
  ["registro_produccion", "Factura de material"],
  ["documento_origen", "Orden de compra / Ficha técnica"],
  ["factura_combustible", "Factura de combustible"],
  ["boleta_electrica", "Boleta eléctrica"],
  ["registro_transporte", "Documento de transporte"],
  ["otro", "Otro"],
];

const constructionWorkDocumentTypeLabelMap = Object.fromEntries(constructionWorkDocumentTypeOptions);

const constructionEvidenceScopeOptions = [
  { value: "empresa", label: "Constructora activa", helper: "Respalda la información de toda la constructora activa." },
  { value: "unidad", label: "Etapa / frente", helper: "Vincula la evidencia a una etapa o frente de obra." },
  { value: "lote", label: "Obra asociada", helper: "Relaciona el documento con una obra específica." },
  { value: "emision", label: "Registro de emisión asociado", helper: "Vincula la evidencia a un registro de emisión cuando exista." },
  { value: "transporte", label: "Transporte", helper: "Puede quedar como respaldo de traslado o logística de obra." },
];

const constructionEvidenceLinkLabels = {
  vinculada: "Vinculada",
  corporativa: "Sin vínculo",
  sin_vinculo: "Sin vínculo",
};

const constructionEvidenceReviewLabels = {
  sin_revisar: "Pendiente",
  pendiente: "Pendiente",
  validada: "Validada",
  validado: "Validada",
  observada: "Observada",
  rechazada: "Rechazada",
};

const constructionEvidenceTypeLabelMap = Object.fromEntries(constructionEvidenceTypeOptions);

function getConstructionEvidenceTypeLabel(value) {
  return constructionEvidenceTypeLabelMap[value] || "Otro";
}

function getConstructionEvidenceScopeLabel(value) {
  const item = constructionEvidenceScopeOptions.find((option) => option.value === value);
  return item?.label || "Obra asociada";
}

function getConstructionEvidenceLinkLabel(value) {
  return constructionEvidenceLinkLabels[value] || "Sin vínculo";
}

function getConstructionEvidenceReviewLabel(value) {
  return constructionEvidenceReviewLabels[value] || "Pendiente";
}

function getConstructionWorkDocumentTypeLabel(value) {
  return constructionWorkDocumentTypeLabelMap[value] || String(value || "").replace(/_/g, " ").trim() || "Otro";
}

export {
  constructionEvidenceScopeOptions,
  constructionEvidenceTypeOptions,
  constructionWorkDocumentTypeOptions,
  getConstructionEvidenceLinkLabel,
  getConstructionEvidenceReviewLabel,
  getConstructionEvidenceScopeLabel,
  getConstructionEvidenceTypeLabel,
  getConstructionWorkDocumentTypeLabel,
};