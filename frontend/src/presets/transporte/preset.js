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
  dashboardTitle: "Panel logistico",
  primaryKpi: "Emisiones por km",
  categories: ["Combustible", "Flota", "Rutas", "Carga", "Mantencion", "Energia", "Otros"],
  intelligence: transportIntelligence,
  navigation: [
    { view: "dashboard", label: "Panel principal" },
    { view: "emisiones", label: "Emisiones" },
    { view: "constructoras", label: "Empresas" },
    { view: "etapas", label: "Operaciones" },
    { view: "obras", label: "Rutas" },
    { view: "reportes", label: "Reportes" },
    { view: "importaciones", label: "Importacion de datos" },
    { view: "evidencias", label: "Evidencias" },
    { view: "usuarios", label: "Usuarios" },
    { view: "configuracion", label: "Configuracion" },
  ],
};

export default transportePreset;
