export function mapConstructoraOption(constructora) {
  return {
    label: constructora?.nombre || "",
    value: constructora?.constructora_id || "",
  };
}
