const OPEN_MAINTENANCE_STATES = new Set(["programado", "en_proceso", "vencido"]);

// Duplicated on purpose, not imported from `assetFormatters.jsx`: that file
// has no JSX in it but keeps the `.jsx` extension, which plain `node --test`
// cannot load — this file must stay importable from a pure-logic test, so
// it carries its own small label map instead (same convention already used
// by `reportAdapters.js`).
const TYPE_LABELS = { vehiculo: "Vehículo", maquinaria: "Maquinaria", equipo: "Equipo", medidor: "Medidor", infraestructura: "Infraestructura", otro: "Otro" };
const MAINTENANCE_LABELS = { al_dia: "Al día", proxima: "Próxima", vencida: "Vencida" };
const humanize = (value) => String(value || "").replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
export const assetTypeLabel = (value) => TYPE_LABELS[value] || humanize(value) || "Sin tipo";
export const maintenanceAvailabilityLabel = (value) => MAINTENANCE_LABELS[value] || humanize(value);

function toDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/**
 * Buckets an asset into one of 4 fleet-status groups using only fields the
 * backend already returns (`estado` on the asset, `estado`/`fecha_programada`
 * on each embedded `mantenimientos[]` row) — no new backend logic, no
 * invented states. `retirado` folds into "fuera_servicio" (there is no
 * separate bucket for it in the product brief); `requiere_revision` folds
 * into "mantencion_proxima" since it signals an upcoming need, not an
 * active intervention.
 */
export function fleetBucket(asset, { today = new Date() } = {}) {
  if (["fuera_servicio", "retirado"].includes(asset.estado)) return "fuera_servicio";
  const maintenances = Array.isArray(asset.mantenimientos) ? asset.mantenimientos : [];
  if (maintenances.some((item) => item.estado === "en_proceso")) return "en_mantencion";
  const hasOpenMaintenance = asset.estado === "requiere_revision" || maintenances.some((item) => OPEN_MAINTENANCE_STATES.has(item.estado));
  if (hasOpenMaintenance) return "mantencion_proxima";
  return "operativo";
}

export const FLEET_TYPE_GROUP = {
  id: "flota",
  types: ["vehiculo", "maquinaria"],
  heroTitle: "Flota y maquinaria",
  heroDescription: "Vehículos y maquinaria registrados en tu organización.",
};

export const EQUIPMENT_TYPE_GROUP = {
  id: "equipos",
  types: ["equipo", "medidor", "infraestructura", "otro"],
  heroTitle: "Equipos e infraestructura",
  heroDescription: "Equipos, medidores e infraestructura operacional.",
};

export const FLEET_BUCKETS = [
  { key: "operativo", label: "Operativo", color: "#059669" },
  { key: "mantencion_proxima", label: "Mantención próxima", color: "#d97706" },
  { key: "en_mantencion", label: "En mantención", color: "#dc2626" },
  { key: "fuera_servicio", label: "Fuera de servicio", color: "#64748b" },
];

const TYPE_COLORS = {
  vehiculo: "#4338ca",
  maquinaria: "#a16207",
  equipo: "#0369a1",
  medidor: "#0891b2",
  infraestructura: "#57534e",
  otro: "#64748b",
};

/** Every upcoming (`programado`) maintenance record across all assets,
 * flattened with a `priority` derived from how close/overdue it is —
 * `vencida` when the record's own status already says so, or when a
 * still-`programado` record's date has already passed. */
export function upcomingMaintenances(assets, { today = new Date(), limit } = {}) {
  const rows = assets.flatMap((asset) => (Array.isArray(asset.mantenimientos) ? asset.mantenimientos : [])
    .filter((item) => OPEN_MAINTENANCE_STATES.has(item.estado))
    .map((item) => {
      const scheduled = toDate(item.fecha_programada);
      const overdue = item.estado === "vencido" || (item.estado === "programado" && scheduled && scheduled < today);
      return {
        id: item.id,
        assetId: asset.id,
        assetName: asset.nombre,
        tipo: item.tipo,
        fechaProgramada: item.fecha_programada || null,
        estado: item.estado,
        priority: overdue ? "vencida" : "proxima",
      };
    }));
  rows.sort((a, b) => {
    if (a.priority !== b.priority) return a.priority === "vencida" ? -1 : 1;
    return (a.fechaProgramada || "").localeCompare(b.fechaProgramada || "");
  });
  return typeof limit === "number" ? rows.slice(0, limit) : rows;
}

/** Client-side aggregate over the same `getAssets()` response the
 * inventory table already renders — no separate dashboard endpoint exists
 * on the backend today, and none of this recomputes an environmental
 * value, only counts/groups already-real fields. */
export function buildAssetsSummary(assets = [], { today = new Date() } = {}) {
  const buckets = Object.fromEntries(FLEET_BUCKETS.map((bucket) => [bucket.key, 0]));
  const byType = new Map();
  assets.forEach((asset) => {
    buckets[fleetBucket(asset, { today })] += 1;
    const key = asset.tipo || "otro";
    byType.set(key, (byType.get(key) || 0) + 1);
  });
  const total = assets.length;
  const withTelemetry = assets.filter((asset) => Number(asset.sensores_count) > 0).length;
  const upcoming = upcomingMaintenances(assets, { today });
  const upcomingSoon = upcoming.filter((row) => row.priority === "proxima").length;

  return {
    total,
    operativos: buckets.operativo,
    requierenMantencion: buckets.mantencion_proxima + buckets.en_mantencion,
    fueraDeServicio: buckets.fuera_servicio,
    asignadosAObra: 0,
    sinAsignar: total,
    conTelemetria: withTelemetry,
    mantencionesProximas: upcomingSoon,
    fleet: FLEET_BUCKETS.map((bucket) => ({ name: bucket.label, value: buckets[bucket.key], color: bucket.color })),
    byType: [...byType.entries()].map(([tipo, value]) => ({ name: assetTypeLabel(tipo), value, color: TYPE_COLORS[tipo] || TYPE_COLORS.otro })).sort((a, b) => b.value - a.value),
    upcomingMaintenances: upcoming,
  };
}

/** For the inventory table's "Mantención" filter: al_dia / proxima /
 * vencida, read directly off each asset's own maintenance records (not
 * `fleetBucket`, which also folds in the asset's own `estado` and isn't
 * about timing specifically). */
export function maintenanceAvailability(asset, { today = new Date() } = {}) {
  const maintenances = Array.isArray(asset.mantenimientos) ? asset.mantenimientos : [];
  const overdue = maintenances.some((item) => item.estado === "vencido" || (item.estado === "programado" && toDate(item.fecha_programada) && toDate(item.fecha_programada) < today));
  if (overdue) return "vencida";
  const open = maintenances.some((item) => OPEN_MAINTENANCE_STATES.has(item.estado));
  return open ? "proxima" : "al_dia";
}
