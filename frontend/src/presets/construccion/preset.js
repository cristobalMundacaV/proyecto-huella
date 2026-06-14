import { constructionIntelligence } from "./intelligence";

const construccionPreset = {
  key: "construccion",
  name: "Construccion",
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
    { view: "dashboard", label: "Panel principal" },
    { view: "emisiones", label: "Emisiones" },
    { view: "constructoras", label: "Empresas" },
    { view: "etapas", label: "Etapas" },
    { view: "obras", label: "Obras" },
    { view: "reportes", label: "Reportes" },
    { view: "importaciones", label: "Importacion de datos" },
    { view: "evidencias", label: "Evidencias" },
    { view: "usuarios", label: "Usuarios" },
    { view: "configuracion", label: "Configuracion" },
  ],
};

export default construccionPreset;
