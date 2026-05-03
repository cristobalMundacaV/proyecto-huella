export function getValidImportRows(rows = []) {
  return rows.filter((row) => row.status === "valid");
}
