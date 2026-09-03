const fieldLabels = {
  codigo: "Código",
  estado: "Estado",
  obra: "Obra",
  organizacion: "Organización",
  confirmado: "Confirmación",
  non_field_errors: "",
};

const validationMessages = {
  "This field is required.": "Este campo es obligatorio.",
};

function flattenValidationErrors(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return "";

  return Object.entries(data)
    .flatMap(([field, value]) => {
      const messages = Array.isArray(value) ? value : [value];
      const label = fieldLabels[field] ?? field.replaceAll("_", " ");

      return messages
        .filter((message) => typeof message === "string" && message.trim())
        .map((message) => validationMessages[message] || message)
        .map((message) => (label ? `${label}: ${message}` : message));
    })
    .join(" ");
}

export function humanizeApiError(error, fallback = "No pudimos completar la acción. Inténtalo nuevamente.") {
  const status = error?.response?.status;
  const data = error?.response?.data;

  if (status === 403) return "No tienes permisos para realizar esta acción.";
  if (status === 404) return "No encontramos el recurso solicitado o ya no está disponible.";

  if (typeof data?.detail === "string" && data.detail.trim()) return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.filter(Boolean).join(" ");

  return flattenValidationErrors(data) || fallback;
}
