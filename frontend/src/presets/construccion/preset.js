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
    { view: "dashboard", label: "Panel" },
    { view: "inteligencia", label: "Inteligencia" },
    { view: "emisiones", label: "Gestion de Huella" },
    { view: "acciones", label: "Acciones" },
    { view: "operacion", label: "Operacion" },
    { view: "evidencias", label: "Evidencias" },
    { view: "reportes", label: "Reportes" },
    { view: "administracion", label: "Administracion" },
  ],
};

export default construccionPreset;
