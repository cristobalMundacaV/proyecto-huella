import { aserraderoFactors } from "@/presets/aserradero/factors";

export const industrialFactors = {
  ...aserraderoFactors,
  title: "Factores de emision industriales",
  subtitle: "Gestiona factores para energia, combustible, procesos, residuos, agua y transporte.",
  categories: ["Energia", "Combustible", "Procesos", "Residuos", "Agua", "Transporte", "Otros"],
  modules: ["energia", "combustible", "procesos", "residuos", "agua", "transporte"],
};
