export const FLOW_SECTIONS = ["resumen", "registros", "tendencias", "calidad", "sensores"];

/** Pure — no router context needed — so it can be unit-tested directly. */
export function sectionFromPathname(pathname) {
  const last = String(pathname || "").split("/").filter(Boolean).at(-1);
  return FLOW_SECTIONS.includes(last) ? last : "resumen";
}

/** Pure — the workspace base path (flow root) a section path was built from. */
export function flowBaseFromPathname(pathname, section) {
  return section === "resumen"
    ? pathname.replace(/\/$/, "")
    : pathname.replace(/\/(registros|tendencias|calidad|sensores)\/?$/, "");
}
