import { aserraderoFactors } from "@/presets/aserradero/factors";

export const transporteFactors = {
  ...aserraderoFactors,
  title: "Factores de emision logisticos",
  subtitle: "Gestiona factores para combustible, rutas, flota, mantencion y carga.",
  categories: ["Combustible", "Rutas", "Flota", "Mantencion", "Carga", "Otros"],
  modules: ["flota", "viajes", "combustible", "rutas", "mantenciones"],
};
