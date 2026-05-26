const constructionEvidenceTypeOptions = [
  ["guia_despacho", "GuÃ­a de despacho"],
  ["factura_combustible", "Factura de combustible"],
  ["factura_electrica", "Boleta elÃ©ctrica"],
  ["boleta_electrica", "Boleta elÃ©ctrica"],
  ["certificado_proveedor", "Certificado de proveedor"],  ["documento_transporte", "Documento de transporte"],
  ["ticket_pesaje", "Ticket de pesaje"],
  ["registro_maquinaria", "Registro de maquinaria"],
  ["registro_maquinaria", "Registro de maquinaria"],
  ["ficha_tecnica_material", "Ficha tecnica de material"],
  ["otro", "Otro"],
];

const constructionWorkDocumentTypeOptions = [
  ["guia_despacho", "GuÃ­a de despacho"],
  ["factura_material", "Factura de material"],
  ["orden_compra", "Orden de compra"],
  ["factura_combustible", "Factura de combustible"],
  ["boleta_electrica", "Boleta elÃ©ctrica"],
  ["documento_transporte", "Documento de transporte"],
  ["otro", "Otro"],
];

const constructionWorkDocumentTypeLabelMap = Object.fromEntries(constructionWorkDocumentTypeOptions);

const constructionEvidenceScopeOptions = [
  { value: "Constructora", label: "Constructora activa", helper: "Respalda la informaciÃ³n de toda la constructora activa." },
  { value: "unidad", label: "Etapa / frente", helper: "Vincula la evidencia a una etapa o frente de obra." },
  { value: "obra", label: "Obra asociada", helper: "Relaciona el evidencia con una obra especÃ­fica." },
  { value: "emision", label: "Registro de emision asociado", helper: "Vincula la evidencia a un registro de emision cuando exista." },
  { value: "transporte", label: "Transporte", helper: "Puede quedar como respaldo de traslado o logÃ­stica de obra." },
];

const constructionEvidenceLinkLabels = {
  vinculada: "Vinculada",
  corporativa: "Sin vÃ­nculo",
  sin_vinculo: "Sin vÃ­nculo",
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
  return constructionEvidenceLinkLabels[value] || "Sin vÃ­nculo";
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