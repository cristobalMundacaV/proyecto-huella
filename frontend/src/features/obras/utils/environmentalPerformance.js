import { getEnvironmentalDomain } from "../../../shared/config/environmentalDomains.js";

// Carbono Zero was carbon-centric: GEI/tCO2e stood in for "environmental
// performance" as a whole. This module is the presentation-layer boundary
// that keeps flows separate instead: each physical flow (energía, agua,
// combustibles, residuos, ruido, emisiones atmosféricas, suelo, transporte,
// materiales) is read and reported in ITS OWN unit, from data the backend
// already computes (`RegistroFlujoAmbiental`/`ViajeOperacional`/
// `EventoMaterial`, via the existing `/flujos-ambientales/`,
// `/viajes-operacionales/` and `/obras/:id/materiales/` endpoints already
// fetched once per obra by `getWorkOperation`). GEI stays a dimension among
// others (`buildGeiPerformance`), never a stand-in for the rest.
//
// Hard rules enforced here, matching the product's explicit constraints:
//  - never sum values across incompatible units (kWh + m3 + kg + dB);
//  - never fabricate an intensity (value / denominator) without a real,
//    period-comparable denominator on the record itself;
//  - a period-over-period "variación" is only ever computed when both
//    periods actually have data in the SAME unit — otherwise the flow is
//    reported as `hasComparison: false`, never a fabricated "0%" or "—".

const PHYSICAL_DOMAINS = [
  { domain: "energia", flows: ["energia", "generacion_propia"] },
  { domain: "agua", flows: ["agua"] },
  { domain: "combustibles", flows: ["combustible", "combustible_movil", "combustible_estacionario"] },
  { domain: "residuos", flows: ["residuo"] },
  { domain: "ruido", flows: ["ruido"] },
  { domain: "emisiones-atmosfericas", flows: ["emisiones_atmosfericas"] },
  { domain: "suelo", flows: ["suelo"] },
];

function toDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
function monthKey(value) {
  const date = toDate(value);
  return date ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}` : null;
}
function monthLabel(key) {
  if (!key) return "Sin período";
  const [year, month] = key.split("-");
  return new Intl.DateTimeFormat("es-CL", { month: "short", year: "2-digit" }).format(new Date(Number(year), Number(month) - 1, 1)).replace(" de ", " ");
}

/** Sums `mediciones[].valor` per (concepto, unidad) pair, bucketed by the
 * month of `periodo_inicio` (falling back to `periodo_fin`) — the same
 * month-bucket pattern already used for GEI in `reportAdapters.js`, applied
 * here to raw `RegistroFlujoAmbiental` records instead of GEI impacts. */
function monthlyTotalsByUnit(records) {
  const months = new Map(); // monthKey -> Map(unit -> {value, count})
  records.forEach((record) => {
    const key = monthKey(record.periodo_inicio || record.periodo_fin);
    if (!key) return;
    (record.mediciones || []).forEach((medicion) => {
      const unit = medicion.unidad;
      const value = Number(medicion.valor);
      if (!unit || !Number.isFinite(value)) return;
      if (!months.has(key)) months.set(key, new Map());
      const byUnit = months.get(key);
      const current = byUnit.get(unit) || { value: 0, count: 0 };
      byUnit.set(unit, { value: current.value + value, count: current.count + 1 });
    });
  });
  return months;
}

/** The single unit with the most populated months for this flow — mirrors
 * the existing `buildFlowPhysicalCards`' "dominant unit" convention, just
 * computed from raw records instead of a possibly-stale dashboard field. */
function dominantUnit(monthTotals) {
  const coverage = new Map();
  monthTotals.forEach((byUnit) => {
    byUnit.forEach((_, unit) => coverage.set(unit, (coverage.get(unit) || 0) + 1));
  });
  return [...coverage.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || null;
}

/** One physical flow's performance for the period covered by `records` —
 * current value, previous value (only the two most recent populated
 * months), variation, and whether a comparison is actually possible. */
export function buildFlowPerformance(records, domain) {
  const config = PHYSICAL_DOMAINS.find((row) => row.domain === domain);
  const flowRecords = (records || []).filter((record) => (config?.flows || [domain]).includes(record.flujo));
  const info = getEnvironmentalDomain(domain);
  const base = { domain, label: info?.label || domain, icon: info?.icon, text: info?.text, softBg: info?.softBg, border: info?.border, recordCount: flowRecords.length };

  if (!flowRecords.length) {
    return { ...base, unit: null, currentValue: null, currentLabel: null, previousValue: null, previousLabel: null, variation: null, hasComparison: false, state: "sin_datos" };
  }

  const monthTotals = monthlyTotalsByUnit(flowRecords);
  const unit = dominantUnit(monthTotals);
  const months = [...monthTotals.entries()]
    .map(([key, byUnit]) => ({ key, label: monthLabel(key), value: unit ? byUnit.get(unit)?.value ?? null : null }))
    .filter((row) => row.value !== null)
    .sort((a, b) => a.key.localeCompare(b.key));

  if (!months.length) {
    return { ...base, unit, currentValue: null, currentLabel: null, previousValue: null, previousLabel: null, variation: null, hasComparison: false, state: "sin_datos" };
  }

  const current = months.at(-1);
  const previous = months.length > 1 ? months.at(-2) : null;
  const hasComparison = Boolean(previous && previous.value !== 0);
  const variation = hasComparison ? ((current.value - previous.value) / previous.value) * 100 : null;

  return {
    ...base,
    unit,
    currentValue: current.value,
    currentLabel: current.label,
    previousValue: previous?.value ?? null,
    previousLabel: previous?.label ?? null,
    variation,
    hasComparison,
    state: "con_datos",
  };
}

/** Every RegistroFlujoAmbiental-backed physical domain in one pass. Does
 * NOT include transporte or materiales — those have their own dedicated
 * models/builders below, each kept in its own unit. */
export function buildPhysicalFlowPerformances(records) {
  return PHYSICAL_DOMAINS.map((config) => buildFlowPerformance(records, config.domain));
}

/** Transporte stays activity-based (viajes, km, carga), never reduced to
 * "transporte = su GEI". Bucketed by month from each trip's own date so a
 * real period comparison is possible without any new backend call. */
export function buildTransportPerformance(journeys) {
  const trips = Array.isArray(journeys) ? journeys : [];
  const info = getEnvironmentalDomain("transporte");
  const base = { domain: "transporte", label: info?.label || "Transporte", icon: info?.icon, text: info?.text, softBg: info?.softBg, border: info?.border, recordCount: trips.length };
  if (!trips.length) return { ...base, unit: "km", currentValue: null, currentLabel: null, previousValue: null, previousLabel: null, variation: null, hasComparison: false, state: "sin_datos", tripsInPeriod: 0 };

  const months = new Map();
  trips.forEach((trip) => {
    const key = monthKey(trip.fecha_salida || trip.fecha_inicio || trip.created_at);
    if (!key) return;
    const km = Number(trip.metricas?.distancia_km ?? trip.distancia_km);
    if (!Number.isFinite(km)) return;
    const current = months.get(key) || { km: 0, viajes: 0 };
    months.set(key, { km: current.km + km, viajes: current.viajes + 1 });
  });
  const ordered = [...months.entries()].map(([key, row]) => ({ key, label: monthLabel(key), ...row })).sort((a, b) => a.key.localeCompare(b.key));
  if (!ordered.length) return { ...base, unit: "km", currentValue: null, currentLabel: null, previousValue: null, previousLabel: null, variation: null, hasComparison: false, state: "sin_datos", tripsInPeriod: 0 };

  const current = ordered.at(-1);
  const previous = ordered.length > 1 ? ordered.at(-2) : null;
  const hasComparison = Boolean(previous && previous.km !== 0);
  return {
    ...base,
    unit: "km",
    currentValue: current.km,
    currentLabel: current.label,
    previousValue: previous?.km ?? null,
    previousLabel: previous?.label ?? null,
    variation: hasComparison ? ((current.km - previous.km) / previous.km) * 100 : null,
    hasComparison,
    state: "con_datos",
    tripsInPeriod: current.viajes,
  };
}

/** Materiales never gets a single fabricated total across materials with
 * different units (concrete in m3, steel in kg, etc. cannot be added). This
 * reports only the single material with the most received activity, in ITS
 * OWN unit, and names how many other materials exist without folding them
 * in. Period comparison is deliberately NOT attempted here: `operation.materials`
 * is a balance snapshot, not confirmed to be split into comparable monthly
 * windows — presenting a fabricated trend on top of an unverified period
 * boundary would risk a misleading tendency, so this is left as a
 * documented gap instead (see product doc). */
export function buildMaterialsPerformance(materials) {
  const rows = Array.isArray(materials) ? materials : [];
  const info = getEnvironmentalDomain("materiales");
  const base = { domain: "materiales", label: info?.label || "Materiales", icon: info?.icon, text: info?.text, softBg: info?.softBg, border: info?.border, recordCount: rows.length };
  const ranked = rows
    .map((row) => ({ name: row.nombre || row.codigo || "Material sin nombre", unit: row.unidad, value: Number(row.ingresos_periodo) }))
    .filter((row) => row.unit && Number.isFinite(row.value))
    .sort((a, b) => b.value - a.value);

  if (!ranked.length) return { ...base, unit: null, currentValue: null, currentLabel: null, previousValue: null, previousLabel: null, variation: null, hasComparison: false, state: "sin_datos", dominantMaterial: null, otherMaterialsCount: 0 };

  const [top, ...rest] = ranked;
  return {
    ...base,
    unit: top.unit,
    currentValue: top.value,
    currentLabel: null,
    previousValue: null,
    previousLabel: null,
    variation: null,
    hasComparison: false,
    state: "con_datos",
    dominantMaterial: top.name,
    otherMaterialsCount: rest.length,
  };
}

/** GEI stays a separate technical block — never blended into the physical
 * flows above. Reuses the backend's own `dashboard.kpis` (no recompute).
 * `intensity` is left null: the only requirement it would need
 * (`Obra.superficie_m2` populated and period-comparable) is not backed by
 * real data today — see docs/product gaps, not fabricated here. */
export function buildGeiPerformance(dashboard) {
  const kpis = dashboard?.kpis || {};
  const total = kpis.huella_total_tco2e;
  return {
    total: total ?? null,
    scope1: kpis.alcance_1_tco2e ?? null,
    scope2: kpis.alcance_2_tco2e ?? null,
    scope3: kpis.alcance_3_tco2e ?? null,
    intensity: null,
    intensityUnavailableReason: "No existe una superficie u otro denominador de actividad registrado y comparable en el período.",
    hasData: total !== null && total !== undefined,
    // Documented, not silently fixed: the backend's own test suite
    // (`test_obra_environmental_dashboard.py`) locks `huella_total_tco2e` to
    // `material_ledger_totals` only — combustibles/energía/transporte GEI are
    // not part of this total today. See docs/product gaps.
    scopeCaveat: "Este total refleja el motor de gases de efecto invernadero vigente para materiales; combustibles, energía y transporte se muestran en su propia unidad física más abajo.",
  };
}

/** Assembles the full "Balance de flujos ambientales" — one entry per flow,
 * each in its own unit, GEI kept separate. */
export function buildEnvironmentalBalance({ records, journeys, materials } = {}) {
  return [
    ...buildPhysicalFlowPerformances(records || []),
    buildTransportPerformance(journeys || []),
    buildMaterialsPerformance(materials || []),
  ];
}

/** Up to `max` flows worth calling out — ranked by (1) having an actual
 * comparison, (2) magnitude of variation — never GEI-first by default, and
 * never repeating the same flow more than once unless it is the only flow
 * with real signal. */
export function pickRelevantFlows(balance, { max = 3 } = {}) {
  const withData = balance.filter((flow) => flow.state === "con_datos");
  const ranked = [...withData].sort((a, b) => {
    if (a.hasComparison !== b.hasComparison) return a.hasComparison ? -1 : 1;
    return Math.abs(b.variation || 0) - Math.abs(a.variation || 0);
  });
  return ranked.slice(0, max);
}

/** A short, non-carbon-first executive narrative naming the flows that
 * actually carry signal this period. Falls back to an honest "sin datos
 * suficientes" line rather than defaulting to a GEI sentence. */
export function buildMultiFlowNarrative(balance) {
  const relevant = pickRelevantFlows(balance, { max: 2 });
  if (!relevant.length) return "El período todavía no registra suficiente información física para describir la presión ambiental dominante.";
  const pieces = relevant.map((flow) => flow.label.toLowerCase());
  const pressure = pieces.length > 1 ? `${pieces[0]} y ${pieces[1]}` : pieces[0];
  const trendPart = relevant
    .filter((flow) => flow.hasComparison)
    .map((flow) => `${flow.label} ${flow.variation > 0 ? "aumentó" : flow.variation < 0 ? "mejoró" : "se mantuvo estable"} respecto al período anterior`)
    .join("; ");
  return `La principal presión ambiental del período proviene de ${pressure}.${trendPart ? ` ${trendPart}.` : ""}`;
}
