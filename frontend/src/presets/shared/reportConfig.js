function parseReportDate(value) {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function getEmissionValue(row) {
  return Number(row?.emisiones_kg_co2e ?? row?.emisiones ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0;
}

function getMetadata(row) {
  return row?.metadata && typeof row.metadata === "object" ? row.metadata : {};
}

function normalizeReportRows(rows) {
  const list = Array.isArray(rows)
    ? rows
    : rows?.results || rows?.data || rows?.datos || rows?.registros || rows?.registros_emision || [];

  return list.map((row) => ({
    ...row,
    emisiones: getEmissionValue(row),
    metadata: getMetadata(row),
  }));
}

function filterRowsByDate(rows, filters = {}) {
  const start = parseReportDate(filters.fecha_inicio);
  const end = parseReportDate(filters.fecha_fin);

  return normalizeReportRows(rows)
    .filter((row) => {
      const rowDate = parseReportDate(row.fecha);
      if (start && (!rowDate || rowDate < start)) return false;
      if (end && (!rowDate || rowDate > end)) return false;
      return true;
    })
    .sort((left, right) => String(right.fecha || "").localeCompare(String(left.fecha || "")) || Number(right.id || 0) - Number(left.id || 0));
}

function groupReportRows(rows, resolver) {
  const grouped = new Map();
  normalizeReportRows(rows).forEach((row) => {
    const key = resolver(row) || "Sin datos";
    const current = grouped.get(key) || {
      key,
      label: key,
      emisiones: 0,
      registros: 0,
      rows: [],
    };
    current.emisiones += getEmissionValue(row);
    current.registros += 1;
    current.rows.push(row);
    grouped.set(key, current);
  });
  return Array.from(grouped.values()).sort((left, right) => right.emisiones - left.emisiones);
}

function getBucket(row, agrupacion = "mes") {
  const date = parseReportDate(row.fecha);
  if (!date) return { key: "sin-fecha", label: "Sin fecha" };

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  if (agrupacion === "dia") {
    return { key: `${year}-${month}-${day}`, label: date.toLocaleDateString("es-CL") };
  }

  if (agrupacion === "categoria") {
    return { key: row.categoria || "Otros", label: row.categoria || "Otros" };
  }

  if (agrupacion === "modulo") {
    return { key: getMetadata(row).module || "Sin modulo", label: getMetadata(row).module || "Sin modulo" };
  }

  if (agrupacion === "fuente") {
    return { key: row.fuente_emision || "Sin fuente", label: row.fuente_emision || "Sin fuente" };
  }

  if (agrupacion === "proveedor") {
    const proveedor = row.proveedor || getMetadata(row).proveedor_madera || getMetadata(row).origen || "Sin proveedor";
    return { key: proveedor, label: proveedor };
  }

  if (agrupacion === "lote") {
    const lote = getMetadata(row).lote || "Sin lote";
    return { key: lote, label: lote };
  }

  const label = date.toLocaleDateString("es-CL", { month: "short", year: "2-digit" });
  return { key: `${year}-${month}`, label };
}

function buildTemporalSerie(rows, agrupacion = "mes") {
  return groupReportRows(rows, (row) => getBucket(row, agrupacion).key)
    .map((group) => {
      const firstRow = group.rows[0];
      return {
        key: group.key,
        label: getBucket(firstRow, agrupacion).label,
        emisiones: group.emisiones,
        registros: group.registros,
      };
    })
    .sort((left, right) => String(left.key).localeCompare(String(right.key)));
}

function buildCommonReportKpis(rows) {
  const normalized = normalizeReportRows(rows);
  const total = normalized.reduce((sum, row) => sum + getEmissionValue(row), 0);
  const bySource = groupReportRows(normalized, (row) => row.fuente_emision || "Sin fuente");
  const byCategory = groupReportRows(normalized, (row) => getMetadata(row).aserradero_category || row.categoria || "Otros");

  return {
    total,
    records: normalized.length,
    criticalSource: bySource[0]?.label || "Sin datos",
    criticalSourceEmissions: bySource[0]?.emisiones || 0,
    criticalCategory: byCategory[0]?.label || "Sin datos",
    criticalCategoryEmissions: byCategory[0]?.emisiones || 0,
  };
}

function getRecordsWithoutFactor(rows) {
  return normalizeReportRows(rows).filter((row) => !Number(row.factor_emision || 0));
}

function formatReportNumber(value, decimals = 1) {
  return Number(value || 0).toLocaleString("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export {
  buildCommonReportKpis,
  buildTemporalSerie,
  filterRowsByDate,
  formatReportNumber,
  getEmissionValue,
  getMetadata,
  getRecordsWithoutFactor,
  groupReportRows,
  normalizeReportRows,
  parseReportDate,
};
