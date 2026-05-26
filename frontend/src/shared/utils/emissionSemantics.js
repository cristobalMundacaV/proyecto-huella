export function normalizeEmissionText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[_\-\u2010-\u2015/]+/g, " ")
    .replace(/[^a-z0-9\s]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function fields(row = {}) {
  return {
    categoria: normalizeEmissionText(row.categoria),
    sourceKey: normalizeEmissionText(row.fuente_emision_key),
    fuente_emision: normalizeEmissionText(row.fuente_emision),
    unidad: normalizeEmissionText(row.unidad),
  };
}

export function isDieselEmission(row) {
  const { categoria, sourceKey, fuente_emision } = fields(row);
  const hasDiesel = sourceKey.includes("diesel") || fuente_emision.includes("diesel");
  return hasDiesel && (categoria === "" || categoria === "combustible" || hasDiesel);
}

export function isElectricityEmission(row) {
  const { categoria, sourceKey, fuente_emision, unidad } = fields(row);
  return (
    categoria === "electricidad" ||
    sourceKey.includes("electricidad") ||
    fuente_emision.includes("electricidad") ||
    unidad === "kwh"
  );
}

export function isTransportEmission(row) {
  const { categoria, sourceKey, fuente_emision, unidad } = fields(row);
  const tokens = new Set(`${sourceKey} ${fuente_emision}`.split(" "));
  return (
    categoria === "transporte" ||
    ["camion", "barco", "tren", "avion", "bus", "vehiculo"].some((token) =>
      tokens.has(token)
    ) ||
    unidad.includes("t km") ||
    unidad.includes("km pasajero")
  );
}
