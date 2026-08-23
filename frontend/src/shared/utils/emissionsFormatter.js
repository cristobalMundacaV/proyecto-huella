import { formatNumber } from "./formatters";

export function displayEmissionFromKg(valueKg, { unit = "kg CO2e", decimals = 1 } = {}) {
  const numeric = Number(valueKg);
  if (!Number.isFinite(numeric)) return null;
  const tonnes = unit === "t CO2e";
  const value = tonnes ? numeric / 1000 : numeric;
  return `${formatNumber(value, Math.min(2, Math.max(0, Number(decimals) || 0)))} ${tonnes ? "tCO2e" : "kgCO2e"}`;
}
