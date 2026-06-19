import { constructionIntelligence } from "./intelligence";

const construccionPreset = {
  key: "construccion",
  name: "Construcción",
  entityLabel: "Empresa",
  entityPluralLabel: "Empresas",
  unitLabel: "Obra",
  unitPluralLabel: "Obras",
  processLabel: "Etapa",
  processPluralLabel: "Etapas",
  dashboardTitle: "Panel principal",
  primaryKpi: "Emisiones totales",
  categories: ["Materiales", "Residuos", "Maquinaria", "Energia", "Transporte", "Agua", "Otros"],
  intelligence: constructionIntelligence,
  navigation: [
    { view: "dashboard", label: "Panel principal", core: true },
    { view: "inteligencia", label: "Inteligencia", core: true },
    { view: "emisiones", label: "Emisiones", core: true },
    { view: "factores", label: "Factores de emision", core: true },
    { view: "constructoras", label: "Empresas", core: true },
    { view: "obras", label: "Obras", presetOnly: true },
    { view: "etapas", label: "Etapas", presetOnly: true },
    { view: "evidencias", label: "Evidencias", core: true },
    { view: "importaciones", label: "Importacion de datos", core: true },
    { view: "reportes", label: "Reportes", core: true },
    { view: "usuarios", label: "Usuarios", core: true },
    { view: "configuracion", label: "Configuracion", core: true },
  ],
};

export default construccionPreset;
