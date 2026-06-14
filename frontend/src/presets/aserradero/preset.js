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
  dashboardTitle: "Panel forestal",
  primaryKpi: "Emisiones por produccion",
  categories: ["Materia prima", "Produccion", "Secado", "Energia", "Transporte", "Residuos", "Subproductos", "Otros"],
  intelligence: sawmillIntelligence,
  navigation: [
    { view: "dashboard", label: "Panel principal", core: true },
    { view: "emisiones", label: "Emisiones", core: true },
    { view: "constructoras", label: "Empresas", core: true },
    { view: "recepcion_trozas", label: "Recepcion de trozas", presetOnly: true },
    { view: "produccion", label: "Produccion", presetOnly: true },
    { view: "secado", label: "Secado", presetOnly: true },
    { view: "energia", label: "Energia", presetOnly: true },
    { view: "transporte_forestal", label: "Transporte forestal", presetOnly: true },
    { view: "residuos_subproductos", label: "Residuos / Subproductos", presetOnly: true },
    { view: "evidencias", label: "Evidencias", core: true },
    { view: "importaciones", label: "Importacion de datos", core: true },
    { view: "reportes", label: "Reportes", core: true },
    { view: "usuarios", label: "Usuarios", core: true },
    { view: "configuracion", label: "Configuracion", core: true },
  ],
};

export default aserraderoPreset;
