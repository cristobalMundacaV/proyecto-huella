function getEvidenceMetadata(evidence) {
  return evidence?.metadata_extraccion && typeof evidence.metadata_extraccion === "object"
    ? evidence.metadata_extraccion
    : {};
}

function normalizeEvidenceRows(rows) {
  const list = Array.isArray(rows) ? rows : rows?.results || rows?.data || rows?.evidencias || [];
  return list.map((row) => ({
    ...row,
    metadata: getEvidenceMetadata(row),
    evidenceType: getEvidenceMetadata(row).evidence_type || row.tipo_evidencia || "otro",
  }));
}

function groupEvidenceByType(rows) {
  return normalizeEvidenceRows(rows).reduce((groups, row) => {
    const key = row.evidenceType || row.tipo_evidencia || "otro";
    groups[key] = (groups[key] || 0) + 1;
    return groups;
  }, {});
}

function groupEvidenceByStatus(rows) {
  return normalizeEvidenceRows(rows).reduce((groups, row) => {
    const key = getEvidenceStatus(row).key;
    groups[key] = (groups[key] || 0) + 1;
    return groups;
  }, {});
}

function getPendingEvidenceTypes(rows, requiredTypes = []) {
  const byType = groupEvidenceByType(rows);
  return requiredTypes.filter((type) => !byType[type.key]);
}

function getEvidenceCoverage(rows, requiredTypes = []) {
  if (!requiredTypes.length) return 100;
  const pending = getPendingEvidenceTypes(rows, requiredTypes);
  return ((requiredTypes.length - pending.length) / requiredTypes.length) * 100;
}

function getEvidenceStatus(row) {
  const value = row?.estado_documental || row?.estado_revision || row?.estado || "pendiente";
  const normalized = String(value).toLowerCase();
  if (normalized.includes("validada") || normalized.includes("validado") || normalized.includes("vinculada")) {
    return { key: "completa", label: "Completa", tone: "success" };
  }
  if (normalized.includes("observada") || normalized.includes("incompleta")) {
    return { key: "incompleta", label: "Incompleta", tone: "warning" };
  }
  if (normalized.includes("rechazada") || normalized.includes("critica")) {
    return { key: "critica", label: "Critica", tone: "danger" };
  }
  if (normalized.includes("sin_vinculo")) {
    return { key: "sin_vincular", label: "Sin vincular", tone: "neutral" };
  }
  return { key: "pendiente", label: "Pendiente revision", tone: "warning" };
}

function formatEvidenceDate(value) {
  if (!value) return "Sin fecha";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("es-CL");
}

function countByMetadata(rows, field) {
  return new Set(normalizeEvidenceRows(rows).map((row) => row.metadata?.[field]).filter(Boolean)).size;
}

function countMatching(rows, predicate) {
  return normalizeEvidenceRows(rows).filter(predicate).length;
}

export {
  countByMetadata,
  countMatching,
  formatEvidenceDate,
  getEvidenceCoverage,
  getEvidenceMetadata,
  getEvidenceStatus,
  getPendingEvidenceTypes,
  groupEvidenceByStatus,
  groupEvidenceByType,
  normalizeEvidenceRows,
};
