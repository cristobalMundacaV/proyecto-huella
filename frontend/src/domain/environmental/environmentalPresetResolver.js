import {
  DEFAULT_ENVIRONMENTAL_MATRIX_KEY,
  environmentalPresetMatrix,
} from "./environmentalPresetMatrix.js";

const normalize = (value = "") =>
  String(value)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();

export function resolveEnvironmentalPresetKey(company = {}) {
  const preset = normalize(company?.preset || company?.preset_key || company?.tipo || "");
  const rubro = normalize(company?.rubro || company?.industria || company?.sector || "");

  if (rubro.includes("mineria") || rubro.includes("minera")) return "mineria";
  if (rubro.includes("energia") || rubro.includes("generacion")) return "energia";
  if (rubro.includes("acuicultura") || rubro.includes("acuicola")) return "acuicultura";
  if (preset === "construccion") return "construccion";
  if (preset === "aserradero" && rubro.includes("forestal")) return "forestal_aserradero";
  if (preset === "aserradero") return "forestal_aserradero";
  if (preset === "industrial") return "industrial_agroindustria";
  if (preset === "transporte") return environmentalPresetMatrix.transporte ? "transporte" : DEFAULT_ENVIRONMENTAL_MATRIX_KEY;
  if (preset === "energia") return "energia";
  if (preset === "acuicultura") return "acuicultura";

  return DEFAULT_ENVIRONMENTAL_MATRIX_KEY;
}

export function resolveEnvironmentalPreset(company = {}) {
  const key = resolveEnvironmentalPresetKey(company);
  return environmentalPresetMatrix[key] || environmentalPresetMatrix[DEFAULT_ENVIRONMENTAL_MATRIX_KEY];
}
