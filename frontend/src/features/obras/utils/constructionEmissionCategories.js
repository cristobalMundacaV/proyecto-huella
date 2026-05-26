import { normalizeEmissionText } from "@/shared/utils/emissionSemantics";

export const constructionCategories = [
  "Materiales",
  "Transporte",
  "Maquinaria",
  "Energia",
  "Agua",
  "Residuos",
  "Otros",
];

export const constructionFactorSuggestions = [
  "HormigÃ³n H30",
  "Cemento",
  "Acero estructural",
  "Ãridos",
  "Madera estructural",
  "DiÃ©sel maquinaria",
  "Gasolina",
  "Electricidad",
  "Transporte camiÃ³n",
  "Residuos mixtos",
  "Escombros",
  "Yeso-cartÃ³n",
];

const categoryLabelMap = {
  combustible: "Maquinaria",
  combustibles: "Maquinaria",
  electricidad: "Energia",
  energia: "Energia",
  transporte: "Transporte",
  materiales: "Materiales",
  material: "Materiales",
  agua: "Agua",
  residuos: "Residuos",
  residuo: "Residuos",
  otros: "Otros",
};

const categoryTokens = [
  [
    "Materiales",
    [
      "hormigon",
      "cemento",
      "acero",
      "arido",
      
      "yeso",
      "carton",
      "material",
      "fierro",
    ],
  ],
  ["Transporte", ["transporte", "camion", "viaje", "ruta", "km", "flete"]],
  [
    "Maquinaria",
    ["diesel", "maquinaria", "excavadora", "retroexcavadora", "grua", "generador", "compactadora"],
  ],
  ["Energia", ["electricidad", "energia", "kwh", "iluminacion", "electrico"]],
  ["Agua", ["agua", "litros agua", "m3 agua"]],
  ["Residuos", ["residuo", "escombro", "sobrante", "reciclaje", "vertedero"]],
];

export function getConstructionCategoryLabel(category, source = "") {
  const normalizedCategory = normalizeEmissionText(category);

  if (categoryLabelMap[normalizedCategory]) {
    return categoryLabelMap[normalizedCategory];
  }

  const normalizedSource = normalizeEmissionText(`${category || ""} ${source || ""}`);
  const matchedCategory = categoryTokens.find(([, tokens]) =>
    tokens.some((token) => normalizedSource.includes(token))
  );

  return matchedCategory?.[0] || category || "Otros";
}

export function categoryMatchesConstructionFilter(factor, selectedCategory) {
  if (!selectedCategory) {
    return true;
  }

  const inferredCategory = getConstructionCategoryLabel(
    factor?.categoria,
    [factor?.fuente_emision, factor?.fuente_emision_key, factor?.unidad].filter(Boolean).join(" ")
  );

  return inferredCategory === selectedCategory;
}

export function getCategoryFieldCopy(category) {
  const copy = {
    Materiales: {
      sourceLabel: "Material",
      sourcePlaceholder: "HormigÃ³n H30, acero estructural, Ã¡ridos",
      quantityLabel: "Cantidad",
      unitHelp: "mÂ³ Â· kg Â· ton Â· mÂ² Â· unidad",
      note: "Registra materiales relevantes para estimar carbono incorporado.",
    },
    Transporte: {
      sourceLabel: "Fuente de emision",
      sourcePlaceholder: "Transporte camiÃ³n",
      quantityLabel: "Cantidad transportada",
      unitHelp: "ton Â· kg Â· mÂ³ Â· viajes",
      note: "Usa esta categorÃ­a para registrar viajes asociados a materiales, maquinaria o residuos.",
    },
    Maquinaria: {
      sourceLabel: "Equipo o maquinaria",
      sourcePlaceholder: "Excavadora diÃ©sel, grÃºa, generador",
      quantityLabel: "Litros combustible u horas mÃ¡quina",
      unitHelp: "litros diÃ©sel Â· litros gasolina Â· horas mÃ¡quina Â· kWh",
      note: "Controla consumo por equipo, ralentÃ­ y mantenciÃ³n.",
    },
    Energia: {
      sourceLabel: "Fuente energÃ©tica",
      sourcePlaceholder: "Electricidad de faena, generador diÃ©sel",
      quantityLabel: "Consumo",
      unitHelp: "kWh Â· litros diÃ©sel",
      note: "Registra consumo electrico o combustible usado para Energia temporal.",
    },
    Agua: {
      sourceLabel: "Consumo de agua",
      sourcePlaceholder: "Agua de faena",
      quantityLabel: "Consumo",
      unitHelp: "mÂ³ Â· litros",
      note: "Monitorea consumo de agua asociado a la ejecuciÃ³n de obra.",
    },
    Residuos: {
      sourceLabel: "Tipo de residuo",
      sourcePlaceholder: "Escombros, plÃ¡sticos / embalajes, residuos mixtos",
      quantityLabel: "Cantidad",
      unitHelp: "kg Â· ton Â· mÂ³",
      note: "Registra destino y tratamiento cuando exista respaldo documental.",
    },
    Otros: {
      sourceLabel: "Fuente de emision",
      sourcePlaceholder: "Otra fuente de obra",
      quantityLabel: "Cantidad",
      unitHelp: "kg Â· ton Â· mÂ³ Â· kWh Â· unidad",
      note: "Clasifica mejor este registro cuando tengas mÃ¡s contexto.",
    },
  };

  return copy[category] || copy.Otros;
}
