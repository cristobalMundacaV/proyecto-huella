export function isPresent(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

export function cleanRut(value) {
  return String(value || "")
    .replace(/\./g, "")
    .replace(/-/g, "")
    .trim()
    .toUpperCase();
}

export function formatChileanRut(value = "") {
  const normalized = String(value)
    .replace(/[^0-9kK]/g, "")
    .slice(0, 9)
    .toUpperCase();

  if (normalized.length <= 1) return normalized;

  const body = normalized.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${body}-${normalized.slice(-1)}`;
}

export function isValidChileanRut(value) {
  const rut = cleanRut(value);

  if (!/^\d{7,8}[\dK]$/.test(rut)) {
    return false;
  }

  const body = rut.slice(0, -1);
  const verifier = rut.slice(-1);
  let sum = 0;
  let multiplier = 2;

  for (let index = body.length - 1; index >= 0; index -= 1) {
    sum += Number(body[index]) * multiplier;
    multiplier = multiplier === 7 ? 2 : multiplier + 1;
  }

  const remainder = 11 - (sum % 11);
  const expected =
    remainder === 11 ? "0" : remainder === 10 ? "K" : String(remainder);

  return verifier === expected;
}

export function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

export function isValidPhone(value) {
  const normalized = String(value || "").replace(/[^\d+]/g, "");
  return /^(\+?56)?\d{8,9}$/.test(normalized);
}
