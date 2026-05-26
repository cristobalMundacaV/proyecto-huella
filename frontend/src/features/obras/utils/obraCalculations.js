export function sumObraMetric(obras, key) {
  return obras.reduce((total, obra) => total + Number(obra?.[key] || 0), 0);
}
