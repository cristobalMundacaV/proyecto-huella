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
  dashboardTitle: "Dashboard ambiental de obra",
  primaryKpi: "Emisiones totales",
  categories: ["Materiales", "Residuos", "Maquinaria", "Energia", "Transporte", "Agua", "Otros"],
  intelligence: constructionIntelligence,
  navigationExtensions: [],
};

export default construccionPreset;
