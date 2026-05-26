import { normalizeActivityText } from "@/shared/utils/activitySemantics";

export const constructionCategories = [
  "Materiales",
  "Transporte",
  "Maquinaria",
  "Energía",
  "Agua",
  "Residuos",
  "Otros",
];

export const constructionFactorSuggestions = [
  "Hormigón H30",
  "Cemento",
  "Acero estructural",
  "Áridos",
  "Madera estructural",
  "Diésel maquinaria",
  "Gasolina",
  "Electricidad",
  "Transporte camión",
  "Residuos mixtos",
  "Escombros",
  "Yeso-cartón",
];

const categoryLabelMap = {
  combustible: "Maquinaria",
  combustibles: "Maquinaria",
  electricidad: "Energía",
  energia: "Energía",
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
      "madera",
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
  ["Energía", ["electricidad", "energia", "kwh", "iluminacion", "electrico"]],
  ["Agua", ["agua", "litros agua", "m3 agua"]],
  ["Residuos", ["residuo", "escombro", "sobrante", "reciclaje", "vertedero"]],
];

export function getConstructionCategoryLabel(category, source = "") {
  const normalizedCategory = normalizeActivityText(category);

  if (categoryLabelMap[normalizedCategory]) {
    return categoryLabelMap[normalizedCategory];
  }

  const normalizedSource = normalizeActivityText(`${category || ""} ${source || ""}`);
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
    [factor?.actividad, factor?.actividad_key, factor?.unidad].filter(Boolean).join(" ")
  );

  return inferredCategory === selectedCategory;
}

export function getCategoryFieldCopy(category) {
  const copy = {
    Materiales: {
      sourceLabel: "Material",
      sourcePlaceholder: "Hormigón H30, acero estructural, áridos",
      quantityLabel: "Cantidad",
      unitHelp: "m³ · kg · ton · m² · unidad",
      note: "Registra materiales relevantes para estimar carbono incorporado.",
    },
    Transporte: {
      sourceLabel: "Fuente de emisión",
      sourcePlaceholder: "Transporte camión",
      quantityLabel: "Cantidad transportada",
      unitHelp: "ton · kg · m³ · viajes",
      note: "Usa esta categoría para registrar viajes asociados a materiales, maquinaria o residuos.",
    },
    Maquinaria: {
      sourceLabel: "Equipo o maquinaria",
      sourcePlaceholder: "Excavadora diésel, grúa, generador",
      quantityLabel: "Litros combustible u horas máquina",
      unitHelp: "litros diésel · litros gasolina · horas máquina · kWh",
      note: "Controla consumo por equipo, ralentí y mantención.",
    },
    Energía: {
      sourceLabel: "Fuente energética",
      sourcePlaceholder: "Electricidad de faena, generador diésel",
      quantityLabel: "Consumo",
      unitHelp: "kWh · litros diésel",
      note: "Registra consumo eléctrico o combustible usado para energía temporal.",
    },
    Agua: {
      sourceLabel: "Consumo de agua",
      sourcePlaceholder: "Agua de faena",
      quantityLabel: "Consumo",
      unitHelp: "m³ · litros",
      note: "Monitorea consumo de agua asociado a la ejecución de obra.",
    },
    Residuos: {
      sourceLabel: "Tipo de residuo",
      sourcePlaceholder: "Escombros, plásticos / embalajes, residuos mixtos",
      quantityLabel: "Cantidad",
      unitHelp: "kg · ton · m³",
      note: "Registra destino y tratamiento cuando exista respaldo documental.",
    },
    Otros: {
      sourceLabel: "Fuente de emisión",
      sourcePlaceholder: "Otra fuente de obra",
      quantityLabel: "Cantidad",
      unitHelp: "kg · ton · m³ · kWh · unidad",
      note: "Clasifica mejor este registro cuando tengas más contexto.",
    },
  };

  return copy[category] || copy.Otros;
}
