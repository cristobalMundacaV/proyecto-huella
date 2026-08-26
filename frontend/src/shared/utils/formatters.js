const locale = "es-CL";

export const formatNumber = (value, maximumFractionDigits = 2) => {
  if (value === null || value === undefined || value === "") return "Sin datos";
  return new Intl.NumberFormat(locale, { minimumFractionDigits: 0, maximumFractionDigits }).format(Number(value));
};
export const formatPercent = (value, maximumFractionDigits = 1) => value === null || value === undefined ? "Sin datos" : `${formatNumber(value, maximumFractionDigits)}%`;
export const formatCompactNumber = (value) => value === null || value === undefined ? "Sin datos" : new Intl.NumberFormat(locale, { notation: "compact", maximumFractionDigits: 1 }).format(Number(value));
export const formatDate = (value) => {
  if (!value) return "Sin fecha";

  const dateOnlyMatch = String(value).match(
    /^(\d{4})-(\d{2})-(\d{2})$/
  );

  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch;

    const localDate = new Date(
      Number(year),
      Number(month) - 1,
      Number(day)
    );

    return new Intl.DateTimeFormat(locale, {
      dateStyle: "medium",
    }).format(localDate);
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
  }).format(new Date(value));
};
export const formatDateTime = (value) => value ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Sin fecha";
