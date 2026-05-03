export function sumLoteMetric(lotes, key) {
  return lotes.reduce((total, lote) => total + Number(lote?.[key] || 0), 0);
}
