export function normalizeSearchText(value = "") {
  return String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-CL").trim();
}

export function filterSelectOptions(options, query) {
  const normalized = normalizeSearchText(query);
  return normalized ? options.filter((option) => normalizeSearchText(option.label).includes(normalized)) : options;
}
