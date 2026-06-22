import { sawmillIntelligence } from "./intelligence";

const aserraderoPreset = {
  key: "aserradero",
  name: "Aserradero",
  entityLabel: "Empresa",
  entityPluralLabel: "Empresas",
  unitLabel: "Planta",
  unitPluralLabel: "Plantas",
  processLabel: "Proceso",
  processPluralLabel: "Procesos",
  dashboardTitle: "Dashboard forestal",
  primaryKpi: "Emisiones por produccion",
  categories: ["Materia prima", "Produccion", "Secado", "Energia", "Transporte", "Residuos", "Otros"],
  intelligence: sawmillIntelligence,
  navigation: [
    { view: "dashboard", label: "Dashboard" },
    { view: "central_operativa", label: "Central Operativa" },
    { view: "ingesta_inteligente", label: "Ingesta Inteligente" },
    { view: "reportes_regulatorios", label: "Reportes Regulatorios" },
    { view: "copiloto_ambiental", label: "Copiloto Ambiental" },
    { view: "inteligencia", label: "Inteligencia" },
    { view: "emisiones", label: "Gestion de Huella" },
    { view: "acciones", label: "Acciones" },
    { view: "operacion", label: "Operacion" },
    { view: "evidencias", label: "Evidencias" },
    { view: "reportes", label: "Reportes" },
    { view: "administracion", label: "Administracion" },
  ],
};

export default aserraderoPreset;
