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
    { view: "dashboard", label: "Panel principal", core: true },
    { view: "emisiones", label: "Emisiones", core: true },
    { view: "constructoras", label: "Empresas", core: true },
    { view: "obras", label: "Lineas", presetOnly: true },
    { view: "etapas", label: "Procesos", presetOnly: true },
    { view: "evidencias", label: "Evidencias", core: true },
    { view: "importaciones", label: "Importacion de datos", core: true },
    { view: "reportes", label: "Reportes", core: true },
    { view: "usuarios", label: "Usuarios", core: true },
    { view: "configuracion", label: "Configuracion", core: true },
  ],
};

export default industrialPreset;
