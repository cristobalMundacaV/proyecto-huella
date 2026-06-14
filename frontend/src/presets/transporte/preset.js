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
    { view: "dashboard", label: "Panel principal", core: true },
    { view: "emisiones", label: "Emisiones", core: true },
    { view: "factores", label: "Factores de emision", core: true },
    { view: "constructoras", label: "Empresas", core: true },
    { view: "flota", label: "Flota", presetOnly: true },
    { view: "viajes", label: "Viajes", presetOnly: true },
    { view: "combustible", label: "Combustible", presetOnly: true },
    { view: "rutas", label: "Rutas", presetOnly: true },
    { view: "mantenciones", label: "Mantenciones", presetOnly: true },
    { view: "evidencias", label: "Evidencias", core: true },
    { view: "reportes", label: "Reportes", core: true },
    { view: "usuarios", label: "Usuarios", core: true },
    { view: "configuracion", label: "Configuracion", core: true },
  ],
};

export default transportePreset;
