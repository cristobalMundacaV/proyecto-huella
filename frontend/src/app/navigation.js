import { CheckCircle2, ClipboardCheck, Clock3, Boxes, FileBarChart2, FileCheck2, Gauge, Settings, ShieldCheck } from "lucide-react";

export const NAV_ITEMS = {
  home: { id: "home", label: "Inicio", title: "Inicio", description: "Estado ejecutivo de tu portafolio ambiental.", path: "/inicio", icon: Gauge },
  primaryUnit: { id: "primaryUnit", label: "Obras", title: "Obras", description: "Gestiona las obras de tu organización.", path: "/obras", icon: Boxes },
  reports: { id: "reports", label: "Reportes", title: "Reportes", description: "Informes ambientales consolidados por obra y período.", path: "/reportes", icon: FileBarChart2 },
  control: { id: "control", label: "Control", title: "Control", description: "Revisión, gobernanza, calidad y trazabilidad ambiental.", path: "/gobernanza", icon: ShieldCheck },
  administration: { id: "administration", label: "Configuración", title: "Configuración", description: "Organización, usuarios y parámetros de funcionamiento.", path: "/administracion", icon: Settings },
};

const PAGE_CONTEXTS = [
  ["/reportes", "Centro de reportes", "Informes ambientales consolidados por obra y período de preparación."],
  ["/obras/:obraId/resumen", "Resumen de obra", "Estado ejecutivo ambiental de esta obra."],
  ["/obras/:obraId/operacion", "Resumen operacional", "Qué está ocurriendo físicamente en esta obra."],
  ["/obras/:obraId/operacion/energia", "Energía", "Consumos y registros energéticos de la obra."],
  ["/obras/:obraId/operacion/agua", "Agua", "Consumos y registros hídricos de la obra."],
  ["/obras/:obraId/operacion/combustibles", "Combustibles", "Uso de combustibles registrado en la obra."],
  ["/obras/:obraId/operacion/transporte", "Transporte", "Movimientos, distancias y carga de la obra."],
  ["/obras/:obraId/operacion/materiales", "Materiales", "Movimientos y balances de materiales."],
  ["/obras/:obraId/operacion/residuos", "Residuos", "Registros y trazabilidad de residuos."],
  ["/obras/:obraId/operacion/ruido", "Ruido", "Mediciones y registros acústicos."],
  ["/obras/:obraId/operacion/emisiones-atmosfericas", "Emisiones atmosféricas", "Mediciones de fuentes atmosféricas."],
  ["/obras/:obraId/evidencias", "Evidencias", "Respaldo documental y cobertura de la obra."],
  ["/obras/:obraId/problemas", "Problemas y acciones", "Seguimiento desde la detección hasta el cierre."],
  ["/obras/:obraId/cumplimiento", "Cumplimiento", "Obligaciones y estado de cumplimiento."],
  ["/obras/:obraId/timeline", "Historial", "Actividad y cambios de la obra."],
  ["/obras/:obraId/reportes", "Informes", "Lectura ejecutiva y salidas ambientales de la obra."],
  ["/obras/:obraId/control", "Control de obra", "Revisión profesional, gobernanza, discrepancias, expedientes y calidad de esta obra."],
  ["/obras/:obraId/configuracion", "Configuración de obra", "Perfil ambiental, ámbitos, factores, metodologías y parámetros aplicables a esta obra."],
  ["/datos/evidencias", "Evidencias", "Documentos y antecedentes ambientales."],
  ["/datos/importaciones", "Importaciones", "Incorporación gobernada de información."],
  ["/inteligencia", "Inteligencia", "Radar de prioridades ambientales."],
  ["/gobernanza/revision", "Revisión profesional", "Cola de revisión y decisiones profesionales."],
  ["/gobernanza/expedientes", "Expedientes", "Antecedentes preparados para uso formal."],
  ["/gobernanza/calidad", "Calidad y discrepancias", "Control de diferencias y validaciones."],
  ["/gobernanza", "Control", "Gobernanza y control ambiental."],
  ["/administracion", "Configuración", "Parámetros de organización y operación."],
].map(([pattern, title, description]) => ({ pattern, title, description }));

function matchesPattern(pathname, pattern) {
  const path = pathname.split("/").filter(Boolean);
  const target = pattern.split("/").filter(Boolean);
  return path.length === target.length && target.every((part, index) => part.startsWith(":") || part === path[index]);
}

/** The single source of navigation truth: ONE sidebar (Inicio/Obras/
 * Reportes/Control/Configuración) whose targets shift with `scope` —
 * `{ type: "portfolio" }` or `{ type: "obra", obraId }` — instead of a
 * second, obra-specific menu. Deep obra navigation (flows, evidencias,
 * revisión, etc.) lives as in-page links/tabs, never as extra sidebar
 * entries (see ObraResumenPage, OperacionOverviewPage, WorkControlPage,
 * WorkConfigPage). */
export function getUnifiedNavigation({ preset = {}, scope } = {}) {
  const isObra = scope?.type === "obra" && Boolean(scope.obraId);
  const base = isObra ? `/obras/${scope.obraId}` : null;

  const works = { ...NAV_ITEMS.primaryUnit };
  if (preset.unitPluralLabel) {
    works.label = preset.unitPluralLabel;
    works.title = preset.unitPluralLabel;
    works.description = `Gestiona las ${preset.unitPluralLabel.toLowerCase()} de tu organización.`;
  }

  const home = { ...NAV_ITEMS.home, path: isObra ? `${base}/resumen` : "/inicio" };
  const reports = { ...NAV_ITEMS.reports, path: isObra ? `${base}/reportes` : "/reportes" };
  const control = { ...NAV_ITEMS.control, path: isObra ? `${base}/control` : "/gobernanza" };
  const administration = { ...NAV_ITEMS.administration, path: isObra ? `${base}/configuracion` : "/administracion" };

  return { home, groups: [{ id: "platform", label: "", items: [works, reports, control, administration] }] };
}

// Domain key here doubles as: the CapacidadOrganizacion/aplicabilidad
// lookup key (via DOMAIN_CONFIG in operationSelectors.js), the route
// segment under `/obras/:id/operacion/`, AND the ENVIRONMENTAL_DOMAINS
// icon/color key (via its alias table for the one hyphenated case) — one
// name, three lookups, deliberately kept as the single source of truth so
// the sidebar subnav never invents its own routes or capability keys.
export const OBRA_OPERATION_FLOWS = [
  { id: "energy", domain: "energia", label: "Energía" },
  { id: "water", domain: "agua", label: "Agua" },
  { id: "fuel", domain: "combustibles", label: "Combustibles" },
  { id: "transport", domain: "transporte", label: "Transporte" },
  { id: "materials", domain: "materiales", label: "Materiales" },
  { id: "waste", domain: "residuos", label: "Residuos" },
  { id: "noise", domain: "ruido", label: "Ruido" },
  { id: "atmosphericEmissions", domain: "emisiones-atmosfericas", label: "Emisiones atmosféricas" },
];

/** The obra-scoped subnav shown UNDER the same five unified sidebar items
 * (never a second sidebar) when the current context is an obra — this is
 * the compact "OBRA ACTIVA" section: Operación (resumen + the 8 flows) and
 * Gestión (evidencias/problemas/cumplimiento/historial). Every path here
 * is an existing route (see router.jsx); this never creates a new page. */
export function getObraContextualSubnav(obraId) {
  const base = `/obras/${obraId}`;
  return {
    groups: [
      {
        id: "operation",
        label: "Operación",
        items: [
          { id: "operationOverview", label: "Resumen operacional", path: `${base}/operacion`, domain: "operacion" },
          ...OBRA_OPERATION_FLOWS.map((flow) => ({
            id: flow.id,
            label: flow.label,
            path: `${base}/operacion/${flow.domain}`,
            domain: flow.domain,
          })),
        ],
      },
      {
        id: "management",
        label: "Gestión",
        items: [
          { id: "evidence", label: "Evidencias", path: `${base}/evidencias`, icon: FileCheck2 },
          { id: "problems", label: "Problemas y acciones", path: `${base}/problemas`, icon: CheckCircle2 },
          { id: "compliance", label: "Cumplimiento", path: `${base}/cumplimiento`, icon: ClipboardCheck },
          { id: "history", label: "Historial", path: `${base}/timeline`, icon: Clock3 },
        ],
      },
    ],
  };
}

/** Backward-compatible portfolio-scope alias — most callers only ever
 * needed the organization-level menu before the context selector existed. */
export function getNavigationForPreset(preset = {}) {
  return getUnifiedNavigation({ preset, scope: { type: "portfolio" } });
}

export function getPageContext(pathname, preset, scope) {
  const exact = [...PAGE_CONTEXTS].sort((a, b) => b.pattern.length - a.pattern.length).find((item) => matchesPattern(pathname, item.pattern));
  if (exact) return exact;
  const navigation = getUnifiedNavigation({ preset, scope: scope || { type: "portfolio" } });
  const item = [navigation.home, ...navigation.groups.flatMap((group) => group.items)].sort((a, b) => b.path.length - a.path.length).find((candidate) => pathname === candidate.path || pathname.startsWith(`${candidate.path}/`));
  return item ? { title: item.title || item.label, description: item.description || "" } : { title: "Carbono Zero", description: "Gestión e inteligencia ambiental para tu organización." };
}

export const navigationForPreset = getNavigationForPreset;
