import { aserraderoFactors } from "@/presets/aserradero/factors";

export const construccionFactors = {
  ...aserraderoFactors,
  title: "Factores de emision de construccion",
  subtitle: "Gestiona factores para materiales, maquinaria, transporte, energia, residuos y agua.",
  categories: ["Materiales", "Maquinaria", "Transporte", "Energia", "Residuos", "Agua", "Otros"],
  modules: ["obras", "etapas", "materiales", "maquinaria", "transporte", "residuos"],
};
