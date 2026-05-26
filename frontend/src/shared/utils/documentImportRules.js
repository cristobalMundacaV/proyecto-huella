import { getCategoryFieldCopy, getConstructionCategoryLabel } from "@/features/obras/utils/constructionEmissionCategories";
import { normalizeEmissionText } from "@/shared/utils/emissionSemantics";

const CATEGORY_RULES = [
  {
    category: "Maquinaria",
    source: "Diésel maquinaria",
    unit: "litros",
    tokens: ["diesel", "diessel", "combustible", "maquinaria", "excavadora", "retroexcavadora", "generador", "grua"],
    quantityPatterns: [
      /(?:litros|lts|l)\s*:?[ \t]*([0-9]+(?:[.,][0-9]+)?)/i,
      /([0-9]+(?:[.,][0-9]+)?)[ \t]*(?:litros|lts|l\b)/i,
    ],
  },
  {
    category: "Energia",
    source: "Electricidad",
    unit: "kWh",
    tokens: ["electricidad", "energia", "kwh", "boleta electrica", "consumo electrico"],
    quantityPatterns: [
      /(?:kwh)\s*:?[ \t]*([0-9]+(?:[.,][0-9]+)?)/i,
      /([0-9]+(?:[.,][0-9]+)?)[ \t]*kwh/i,
    ],
  },
  {
    category: "Transporte",
    source: "Transporte camión",
    unit: "km",
    tokens: ["transporte", "camion", "flete", "viaje", "ruta", "patente"],
    quantityPatterns: [
      /(?:km|kilometros)\s*:?[ \t]*([0-9]+(?:[.,][0-9]+)?)/i,
      /([0-9]+(?:[.,][0-9]+)?)[ \t]*(?:km|kilometros)/i,
    ],
  },
  {
    category: "Materiales",
    source: "Hormigón H30",
    unit: "m3",
    tokens: ["hormigon", "concreto", "cemento", "acero", "arido",  "material"],
    quantityPatterns: [
      /(?:m3|m\xB3|metros? cubicos?)\s*:?[ \t]*([0-9]+(?:[.,][0-9]+)?)/i,
      /([0-9]+(?:[.,][0-9]+)?)[ \t]*(?:m3|m\xB3|metros? cubicos?)/i,
      /(?:ton|toneladas?)\s*:?[ \t]*([0-9]+(?:[.,][0-9]+)?)/i,
    ],
  },
  {
    category: "Agua",
    source: "Agua de faena",
    unit: "m3",
    tokens: ["agua", "consumo de agua", "m3 agua", "litros agua"],
    quantityPatterns: [
      /(?:m3|m\xB3|metros? cubicos?)\s*:?[ \t]*([0-9]+(?:[.,][0-9]+)?)/i,
      /([0-9]+(?:[.,][0-9]+)?)[ \t]*(?:m3|m\xB3|metros? cubicos?)/i,
    ],
  },
  {
    category: "Residuos",
    source: "Residuos mixtos",
    unit: "ton",
    tokens: ["residuo", "escombro", "sobrante", "retiro", "vertedero", "reciclaje"],
    quantityPatterns: [
      /(?:ton|toneladas?)\s*:?[ \t]*([0-9]+(?:[.,][0-9]+)?)/i,
      /([0-9]+(?:[.,][0-9]+)?)[ \t]*(?:ton|toneladas?)/i,
    ],
  },
];

function normalizeNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }

  return String(value).replace(/\s+/g, "").replace(/\.(?=\d{3}(?:\D|$))/g, "").replace(",", ".");
}

function numberFromValue(value) {
  const normalized = normalizeNumber(value);
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function firstMatchingPattern(text, patterns) {
  for (const pattern of patterns) {
    const match = String(text || "").match(pattern);
    if (match?.[1]) {
      return match[1];
    }
  }
  return "";
}

function scoreFactor(factor, category, source, unit) {
  const haystack = normalizeEmissionText(
    [factor?.categoria, factor?.fuente_emision, factor?.fuente_emision_key, factor?.unidad, factor?.fuente].filter(Boolean).join(" ")
  );
  let score = 0;

  if (category && getConstructionCategoryLabel(factor?.categoria, factor?.fuente_emision) === category) {
    score += 6;
  }

  if (source && haystack.includes(normalizeEmissionText(source))) {
    score += 4;
  }

  if (unit && normalizeEmissionText(factor?.unidad) === normalizeEmissionText(unit)) {
    score += 3;
  }

  CATEGORY_RULES.forEach((rule) => {
    if (rule.category === category && rule.tokens.some((token) => haystack.includes(token))) {
      score += 2;
    }
  });

  return score;
}

function inferCategory(text, structured = {}) {
  const combined = normalizeEmissionText(
    [text, structured?.proveedor, structured?.origen, structured?.destino, structured?.numero_evidencia].filter(Boolean).join(" ")
  );

  const matchedRule = CATEGORY_RULES.find((rule) => rule.tokens.some((token) => combined.includes(token)));

  if (matchedRule) {
    return matchedRule;
  }

  const structuredHints = [structured?.litros_combustible, structured?.kwh, structured?.volumen]
    .some((value) => value !== undefined && value !== null && value !== "");

  if (structuredHints) {
    return CATEGORY_RULES[0];
  }

  return {
    category: "Otros",
    source: "Otra fuente de obra",
    unit: "unidad",
    tokens: [],
    quantityPatterns: [/([0-9]+(?:[.,][0-9]+)?)/i],
  };
}

function inferQuantity(rule, text, structured = {}) {
  const structuredCandidates = [
    structured?.litros_combustible,
    structured?.kwh,
    structured?.volumen,
    structured?.cantidad,
    structured?.monto,
  ];

  for (const candidate of structuredCandidates) {
    const parsed = numberFromValue(candidate);
    if (parsed !== null) {
      return parsed;
    }
  }

  const matched = firstMatchingPattern(text, rule.quantityPatterns || []);
  const parsed = numberFromValue(matched);
  return parsed === null ? null : parsed;
}

export function inferDocumentImportSuggestion({ text = "", structured = {}, fileName = "", factors = [] }) {
  const normalizedText = String(text || "");
  const rule = inferCategory(normalizedText, structured);
  const quantity = inferQuantity(rule, normalizedText, structured);
  const copy = getCategoryFieldCopy(rule.category);
  const inferredSource = structured?.proveedor || structured?.origen || structured?.destino || rule.source;
  const docDate = structured?.fecha || "";

  const factorSuggestions = Array.isArray(factors)
    ? [...factors]
        .sort((left, right) => scoreFactor(right, rule.category, inferredSource, rule.unit) - scoreFactor(left, rule.category, inferredSource, rule.unit))
        .slice(0, 3)
    : [];
  const suggestedFactor = factorSuggestions[0] || null;

  const source = inferredSource || copy.sourcePlaceholder || rule.source;
  const unit = structured?.kwh ? "kWh" : structured?.litros_combustible ? "litros" : rule.unit;
  const confidenceScore = [normalizedText, quantity, suggestedFactor].filter(Boolean).length + (structured?.fecha ? 1 : 0);

  let confidence = "baja";
  if (confidenceScore >= 4) {
    confidence = "alta";
  } else if (confidenceScore >= 2) {
    confidence = "media";
  }

  return {
    document: {
      fileName,
      date: docDate,
      type: structured?.tipo_evidencia || "evidencia de obra",
      provider: structured?.proveedor || "",
      number: structured?.numero_evidencia || "",
      confidence,
      text,
    },
    emission: {
      category: rule.category,
      source,
      quantity: quantity === null ? "" : String(quantity),
      unit,
      factorEmision: suggestedFactor?.factor_emision ? String(suggestedFactor.factor_emision) : "",
      factorEmisionId: suggestedFactor?.id || suggestedFactor?.factor_emision_id || "",
      factorLabel: suggestedFactor?.label || suggestedFactor?.fuente_emision || "",
      estimatedEmissions:
        quantity !== null && suggestedFactor?.factor_emision
          ? String((quantity * Number(suggestedFactor.factor_emision)).toFixed(3))
          : "",
      factorSuggestions,
    },
    review: {
      confidence,
      needsReview: confidence !== "alta",
      note:
        confidence === "alta"
          ? "La sugerencia combina texto extraido, categoria probable y un factor de emission compatible."
          : "La sugerencia necesita revision manual antes de crear el registro.",
    },
  };
}
