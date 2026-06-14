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
  dashboardTitle: "Panel industrial",
  primaryKpi: "Emisiones por produccion",
  categories: ["Energia", "Combustibles", "Procesos", "Insumos", "Residuos", "Transporte", "Otros"],
  intelligence: industrialIntelligence,
  navigation: [
    { view: "dashboard", label: "Panel principal" },
    { view: "emisiones", label: "Emisiones" },
    { view: "constructoras", label: "Empresas" },
    { view: "etapas", label: "Procesos" },
    { view: "obras", label: "Lineas" },
    { view: "reportes", label: "Reportes" },
    { view: "importaciones", label: "Importacion de datos" },
    { view: "evidencias", label: "Evidencias" },
    { view: "usuarios", label: "Usuarios" },
    { view: "configuracion", label: "Configuracion" },
  ],
};

export default industrialPreset;
