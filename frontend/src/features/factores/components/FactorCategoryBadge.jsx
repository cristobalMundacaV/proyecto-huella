import Badge from "@/shared/components/Badge";

const CATEGORY_TONES = {
  combustible: "orange",
  combustibles: "orange",
  electricidad: "emerald",
  energia: "emerald",
  energia_electrica: "emerald",
  transporte: "blue",
  residuos: "rose",
  agua: "cyan",
  insumos: "violet",
  materiales: "violet",
  otros: "amber",
};

const normalizeCategory = (category) =>
  String(category || "Otros")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_");

function FactorCategoryBadge({ category }) {
  const label = category || "Otros";
  const tone = CATEGORY_TONES[normalizeCategory(label)] || "lime";

  return <Badge tone={tone}>{label}</Badge>;
}

export default FactorCategoryBadge;
