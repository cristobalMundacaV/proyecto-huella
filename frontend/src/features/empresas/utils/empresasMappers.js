export function mapEmpresaOption(empresa) {
  return {
    label: empresa?.nombre || "",
    value: empresa?.empresa_id || "",
  };
}
