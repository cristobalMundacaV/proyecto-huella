import { industrialIntelligence } from "./intelligence";

const industrialPreset = {
  key: "industrial",
  name: "Industrial",
  entityLabel: "Empresa",
  entityPluralLabel: "Empresas",
  unitLabel: "Linea",
  unitPluralLabel: "Lineas",
  processLabel: "Proceso",
  processPluralLabel: "Procesos",
  dashboardTitle: "Dashboard industrial",
  primaryKpi: "Emisiones por produccion",
  categories: ["Energia", "Combustibles", "Procesos", "Insumos", "Residuos", "Transporte", "Otros"],
  intelligence: industrialIntelligence,
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

export default industrialPreset;
