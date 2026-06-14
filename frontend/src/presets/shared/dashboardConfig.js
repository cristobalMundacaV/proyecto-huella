function getEmissionValue(row) {
  return Number(row?.emisiones_kg_co2e ?? row?.emisiones ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0;
}

function normalizeEmissionRows(rows) {
  const list = Array.isArray(rows)
    ? rows
    : rows?.results || rows?.data || rows?.datos || rows?.registros || rows?.registros_emision || [];

  return list.map((row) => ({
    ...row,
    emisiones: getEmissionValue(row),
    metadata: row?.metadata && typeof row.metadata === "object" ? row.metadata : {},
  }));
}

function sumEmissions(rows) {
  return normalizeEmissionRows(rows).reduce((total, row) => total + getEmissionValue(row), 0);
}

function groupRows(rows, getKey) {
  return normalizeEmissionRows(rows)
    .reduce((groups, row) => {
      const key = getKey(row) || "Sin datos";
      const current = groups.get(key) || {
        key,
        label: key,
        records: 0,
        emissions: 0,
        rows: [],
      };

      current.records += 1;
      current.emissions += getEmissionValue(row);
      current.rows.push(row);
      groups.set(key, current);
      return groups;
    }, new Map());
}

function groupByCategory(rows) {
  return Array.from(
    groupRows(rows, (row) => row.metadata?.aserradero_category || row.categoria_visible || row.categoria || "Otros").values()
  ).sort((left, right) => right.emissions - left.emissions);
}

function groupByMetadataModule(rows) {
  return Array.from(groupRows(rows, (row) => row.metadata?.module || "sin_modulo").values()).sort(
    (left, right) => right.emissions - left.emissions
  );
}

function getCriticalCategory(rows) {
  return groupByCategory(rows)[0] || null;
}

function getCriticalModule(rows) {
  return groupByMetadataModule(rows).find((group) => group.key !== "sin_modulo") || null;
}

function getRecordsWithoutFactor(rows) {
  return normalizeEmissionRows(rows).filter((row) => !Number(row?.factor_emision || 0));
}

export {
  getCriticalCategory,
  getCriticalModule,
  getRecordsWithoutFactor,
  groupByCategory,
  groupByMetadataModule,
  normalizeEmissionRows,
  sumEmissions,
};
