import { industrialIntelligence } from "./intelligence";

const industrialPreset = {
  key: "industrial",
  name: "Industrial",
  entityLabel: "Empresa",
  entityPluralLabel: "Empresas",
  unitLabel: "Línea",
  unitPluralLabel: "Líneas",
  processLabel: "Proceso",
  processPluralLabel: "Procesos",
  dashboardTitle: "Dashboard industrial",
  primaryKpi: "Emisiones por produccion",
  categories: ["Energia", "Combustibles", "Procesos", "Insumos", "Residuos", "Transporte", "Otros"],
  intelligence: industrialIntelligence,
  navigationProfile: { operation: ["primaryUnit", "assets", "sensors"] },
  navigationExtensions: [],
};

export default industrialPreset;
