import { transportIntelligence } from "./intelligence";

const transportePreset = {
  key: "transporte",
  name: "Transporte",
  entityLabel: "Empresa",
  entityPluralLabel: "Empresas",
  unitLabel: "Ruta",
  unitPluralLabel: "Rutas",
  processLabel: "Operacion",
  processPluralLabel: "Operaciones",
  dashboardTitle: "Dashboard logistico",
  primaryKpi: "Emisiones por km",
  categories: ["Combustible", "Flota", "Rutas", "Carga", "Mantencion", "Energia", "Otros"],
  intelligence: transportIntelligence,
  navigationExtensions: [],
};

export default transportePreset;
