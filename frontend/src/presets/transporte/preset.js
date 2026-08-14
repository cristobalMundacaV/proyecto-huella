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

export default transportePreset;
