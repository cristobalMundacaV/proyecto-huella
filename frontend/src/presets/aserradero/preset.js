import { sawmillIntelligence } from "./intelligence";

const aserraderoPreset = {
  key: "aserradero",
  name: "Aserradero",
  entityLabel: "Empresa",
  entityPluralLabel: "Empresas",
  unitLabel: "Planta",
  unitPluralLabel: "Plantas",
  processLabel: "Proceso",
  processPluralLabel: "Procesos",
  dashboardTitle: "Dashboard forestal",
  primaryKpi: "Emisiones por produccion",
  categories: ["Materia prima", "Produccion", "Secado", "Energia", "Transporte", "Residuos", "Otros"],
  intelligence: sawmillIntelligence,
  navigation: [
    { view: "dashboard", label: "Dashboard" },
    { view: "diagnostico", label: "Diagnostico Ambiental" },
    { view: "operacion", label: "Operacion" },
    { view: "inteligencia", label: "Inteligencia" },
    { view: "copiloto_ambiental", label: "Copiloto Ambiental" },
    { view: "acciones", label: "Acciones" },
    { view: "evidencias", label: "Evidencias Ambientales" },
    { view: "administracion", label: "Administracion" },
  ],
};

export default aserraderoPreset;
