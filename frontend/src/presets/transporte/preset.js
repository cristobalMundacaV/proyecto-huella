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
    { view: "reportes_regulatorios", label: "Reportes Regulatorios" },
    { view: "copiloto_ambiental", label: "Copiloto Ambiental" },
    { view: "inteligencia", label: "Inteligencia" },
    { view: "emisiones", label: "Gestion de Huella" },
    { view: "acciones", label: "Acciones" },
    { view: "operacion", label: "Operacion" },
    { view: "evidencias", label: "Evidencias Ambientales" },
    { view: "reportes", label: "Reportes" },
    { view: "administracion", label: "Administracion" },
  ],
};

export default transportePreset;
