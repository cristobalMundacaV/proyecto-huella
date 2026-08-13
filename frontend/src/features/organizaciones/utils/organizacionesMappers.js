export function mapOrganizacionOption(organizacion) {
  return {
    label: organizacion?.nombre || "",
    value: organizacion?.organizacion_id || "",
  };
}
