import {
  constructionWorkDocumentTypeOptions,
} from "@/shared/utils/constructionEvidenceLabels";

const balanceTone = {
  favorable: {
    label: "Favorable",
    className: "border-[#BEF264] bg-[#F7FEE7] text-[#3F6212]",
  },
  medio: {
    label: "Medio",
    className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
  },
  critico: {
    label: "Critico",
    className: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
  },
};

const confidenceTone = {
  "Alta confianza": "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
  "Media confianza": "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
  "Baja confianza": "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
};

const documentStatusTone = {
  pendiente: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
  validado: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
  observada: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
  rechazado: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
};

const documentTypes = constructionWorkDocumentTypeOptions;

const ocrFields = [
  ["fecha", "Fecha"],
  ["proveedor", "Proveedor"],
  ["litros_combustible", "Litros combustible"],
  ["kwh", "kWh"],
  ["patente", "Patente"],
  ["origen", "Origen proveedor / planta"],
  ["destino", "Destino obra"],
  ["volumen", "Cantidad base / superficie"],
  ["monto", "Monto"],
  ["numero_evidencia", "Numero evidencia"],
];

const ficha_ambientalTone = {
  "Sin ficha_ambiental": {
    className: "border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)]",
  },
  "FichaAmbiental Base": {
    className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
  },
  "FichaAmbiental Verde": {
    className: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
  },
  "FichaAmbiental Verde Plus": {
    className: "border-[#BEF264] bg-[#F7FEE7] text-[#3F6212]",
  },
};

export {
  balanceTone,
  confidenceTone,
  documentStatusTone,
  documentTypes,
  ocrFields,
  ficha_ambientalTone,
};
