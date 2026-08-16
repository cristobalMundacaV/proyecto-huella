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
  navigationProfile: { operation: ["primaryUnit", "sectorOperations", "assets", "sensors"], processesLabel: "Procesos de planta" },
  navigationExtensions: [
    { path: "/operacion/recepcion-trozas", label: "Recepción de trozas" },
    { path: "/operacion/produccion", label: "Producción" },
    { path: "/operacion/secado", label: "Secado" },
    { path: "/operacion/energia", label: "Energía" },
    { path: "/operacion/transporte-forestal", label: "Transporte forestal" },
    { path: "/operacion/residuos-subproductos", label: "Residuos y subproductos" },
    { path: "/operacion/lotes-forestales", label: "Lotes forestales" },
  ],
};

export default aserraderoPreset;
