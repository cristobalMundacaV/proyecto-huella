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
  categories: ["Materia prima", "Secado", "Energia", "Transporte", "Residuos", "Mantencion", "Otros"],
  navigation: [
    { view: "dashboard", label: "Panel principal" },
    { view: "emisiones", label: "Emisiones" },
    { view: "constructoras", label: "Empresas" },
    { view: "etapas", label: "Procesos" },
    { view: "obras", label: "Plantas" },
    { view: "reportes", label: "Reportes" },
    { view: "importaciones", label: "Importacion de datos" },
    { view: "evidencias", label: "Evidencias" },
    { view: "usuarios", label: "Usuarios" },
    { view: "configuracion", label: "Configuracion" },
  ],
};

export default aserraderoPreset;
