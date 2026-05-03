export function normalizeActivityText(value) {
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
    categoria: normalizeActivityText(row.categoria),
    activityKey: normalizeActivityText(row.activity_key || row.actividad_key),
    actividad: normalizeActivityText(row.actividad),
    unidad: normalizeActivityText(row.unidad),
  };
}

export function isDieselActivity(row) {
  const { categoria, activityKey, actividad } = fields(row);
  const hasDiesel = activityKey.includes("diesel") || actividad.includes("diesel");
  return hasDiesel && (categoria === "" || categoria === "combustible" || hasDiesel);
}

export function isElectricityActivity(row) {
  const { categoria, activityKey, actividad, unidad } = fields(row);
  return (
    categoria === "electricidad" ||
    activityKey.includes("electricidad") ||
    actividad.includes("electricidad") ||
    unidad === "kwh"
  );
}

export function isTransportActivity(row) {
  const { categoria, activityKey, actividad, unidad } = fields(row);
  const tokens = new Set(`${activityKey} ${actividad}`.split(" "));
  return (
    categoria === "transporte" ||
    ["camion", "barco", "tren", "avion", "bus", "vehiculo"].some((token) =>
      tokens.has(token)
    ) ||
    unidad.includes("t km") ||
    unidad.includes("km pasajero")
  );
}
