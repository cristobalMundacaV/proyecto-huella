function normalizeImportRows(rows) {
  return (Array.isArray(rows) ? rows : rows?.rows || rows?.data || []).map((row, index) => ({
    row_number: row.row_number || index + 1,
    status: row.status || (row.errors?.length ? "error" : "valid"),
    data: row.data || row,
    errors: row.errors || [],
    warnings: row.warnings || [],
  }));
}

function getImportRowStatus(row) {
  if (row.status === "valid") return { key: "valid", label: "Valida", tone: "success" };
  if (getImportErrors(row).length) return { key: "error", label: "Error", tone: "danger" };
  if (getImportWarnings(row).length) return { key: "warning", label: "Advertencia", tone: "warning" };
  return { key: "valid", label: "Valida", tone: "success" };
}

function getImportErrors(row) {
  return Array.isArray(row.errors) ? row.errors : [];
}

function getImportWarnings(row) {
  return Array.isArray(row.warnings) ? row.warnings : [];
}

function buildImportSummary(rows) {
  const normalized = normalizeImportRows(rows);
  return {
    total: normalized.length,
    validas: normalized.filter((row) => getImportRowStatus(row).key === "valid").length,
    errores: normalized.filter((row) => getImportErrors(row).length).length,
    advertencias: normalized.filter((row) => getImportWarnings(row).length).length,
    factores_encontrados: normalized.filter((row) => Number(row.data?.factor_emision || 0) > 0).length,
    factores_faltantes: normalized.filter((row) => !Number(row.data?.factor_emision || 0)).length,
    listos: normalized.filter((row) => getImportRowStatus(row).key === "valid").length,
    duplicados: 0,
  };
}

function buildCsvFromRows(rows, columns) {
  const header = columns.join(",");
  const body = rows.map((row) => columns.map((column) => escapeCsv(row[column] ?? "")).join(","));
  return [header, ...body].join("\n");
}

function downloadCsvTemplate(columns, filename) {
  const csv = buildCsvFromRows([], columns);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function mapPresetImportPayload(preset, module, rows, mapper) {
  return normalizeImportRows(rows)
    .filter((row) => getImportRowStatus(row).key === "valid")
    .map((row) => mapper(row.data, { preset, module, rowNumber: row.row_number }));
}

function escapeCsv(value) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

export {
  buildCsvFromRows,
  buildImportSummary,
  downloadCsvTemplate,
  getImportErrors,
  getImportRowStatus,
  getImportWarnings,
  mapPresetImportPayload,
  normalizeImportRows,
};
