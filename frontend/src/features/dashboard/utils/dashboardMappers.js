export function mapEmissionEntries(entries = {}) {
  return Object.entries(entries).map(([name, emisiones]) => ({
    emisiones,
    name,
  }));
}
