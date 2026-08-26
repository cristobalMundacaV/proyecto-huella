const PENDING_APPLICABILITY_STATES = new Set([
  "pendiente",
  "no_determinado",
  "sin_datos",
]);

export function getConfirmedWorkCapabilityKeys(applicability = []) {
  return new Set(
    applicability
      .filter((item) => item?.estado_obra === "aplica")
      .map((item) => item?.clave)
      .filter(Boolean),
  );
}

export function hasPendingWorkApplicability(applicability = []) {
  return applicability.some((item) =>
    PENDING_APPLICABILITY_STATES.has(item?.estado_obra),
  );
}

export function isWorkModuleConfirmed(item, confirmedCapabilities) {
  const capabilities = item.capabilities || [item.capability || item.domain];
  return capabilities.some((capability) => confirmedCapabilities.has(capability));
}
