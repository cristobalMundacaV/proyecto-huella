const balanceTone = {
  favorable: {
    label: "Favorable",
    className: "border-lime-400/30 bg-lime-400/10 text-lime-200",
  },
  medio: {
    label: "Medio",
    className: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  },
  critico: {
    label: "Critico",
    className: "border-red-400/30 bg-red-400/10 text-red-200",
  },
};

const confidenceTone = {
  "Alta confianza": "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  "Media confianza": "border-amber-400/30 bg-amber-400/10 text-amber-200",
  "Baja confianza": "border-red-400/30 bg-red-400/10 text-red-200",
};

const documentStatusTone = {
  pendiente: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  validado: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  rechazado: "border-red-400/30 bg-red-400/10 text-red-200",
};

const documentTypes = [
  ["guia_despacho", "Guia de despacho"],
  ["factura_combustible", "Factura de combustible"],
  ["boleta_electrica", "Boleta electrica"],
  ["registro_produccion", "Registro de produccion"],
  ["documento_origen", "Documento de origen"],
  ["registro_transporte", "Registro de transporte"],
];

const ocrFields = [
  ["fecha", "Fecha"],
  ["proveedor", "Proveedor"],
  ["litros_combustible", "Litros combustible"],
  ["kwh", "kWh"],
  ["patente", "Patente"],
  ["origen", "Origen"],
  ["destino", "Destino"],
  ["volumen", "Volumen"],
  ["monto", "Monto"],
  ["numero_documento", "Numero documento"],
];

const pasaporteTone = {
  "Sin pasaporte": {
    className: "border-slate-700 bg-slate-900 text-slate-200",
  },
  "Pasaporte Base": {
    className: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
  },
  "Pasaporte Verde": {
    className: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  },
  "Pasaporte Verde Plus": {
    className: "border-lime-400/30 bg-lime-400/10 text-lime-200",
  },
};

export {
  balanceTone,
  confidenceTone,
  documentStatusTone,
  documentTypes,
  ocrFields,
  pasaporteTone,
};
