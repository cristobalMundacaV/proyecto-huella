export function mapLoteOption(lote) {
  return {
    label: lote?.id_lote || "",
    value: lote?.id_lote || "",
  };
}
