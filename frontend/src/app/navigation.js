import { Activity, CheckCircle2, ClipboardCheck, Clock3, Boxes, Factory, FileBarChart2, FileCheck2, Gauge, LayoutDashboard, Package, Radio, Settings, ShieldCheck, Truck, Wrench } from "lucide-react";

export const NAV_ITEMS = {
  home: { id: "home", label: "Inicio", title: "Inicio", description: "Estado ejecutivo de tu portafolio ambiental.", path: "/inicio", icon: Gauge },
  primaryUnit: { id: "primaryUnit", label: "Obras", title: "Obras", description: "Gestiona las obras de tu organización.", path: "/obras", icon: Boxes },
  assets: { id: "assets", label: "Activos", title: "Activos", description: "Flota, maquinaria, equipos y sensores de tu organización.", path: "/activos", icon: Factory },
  reports: { id: "reports", label: "Reportes", title: "Reportes", description: "Informes ambientales consolidados por obra y período.", path: "/reportes", icon: FileBarChart2 },
  control: { id: "control", label: "Control", title: "Control", description: "Revisión, gobernanza, calidad y trazabilidad ambiental.", path: "/gobernanza", icon: ShieldCheck },
  administration: { id: "administration", label: "Configuración", title: "Configuración", description: "Organización, usuarios y parámetros de funcionamiento.", path: "/administracion", icon: Settings },
};

// Activos (portfolio-only — assets have no obra assignment in the data
// model today, see docs/product) mirrors the obra-scope Operación/Gestión
// pattern: a `.children`-bearing item with NO path of its own, so it is a
// pure expand/collapse toggle handled by the SAME GeneralNavigation code —
// never a second sidebar or a new interaction model.
export const ASSETS_SUBNAV = [
  { id: "assetsOverview", label: "Vista general", path: "/activos", icon: LayoutDashboard },
  { id: "assetsFleet", label: "Flota y maquinaria", path: "/activos/flota", icon: Truck },
  { id: "assetsEquipment", label: "Equipos e infraestructura", path: "/activos/equipos", icon: Package },
  { id: "assetsSensors", label: "Sensores y medidores", path: "/activos/sensores", icon: Radio },
  { id: "assetsMaintenance", label: "Mantenciones", path: "/activos/mantenciones", icon: Wrench },
];

const PAGE_CONTEXTS = [
  ["/activos", "Activos de la organización", "Flota, maquinaria, equipos y sensores que participan en tu operación."],
  ["/activos/flota", "Flota y maquinaria", "Vehículos y maquinaria registrados en tu organización."],
  ["/activos/equipos", "Equipos e infraestructura", "Equipos, medidores e infraestructura operacional."],
  ["/activos/sensores", "Sensores y medidores", "Dispositivos y seguimiento de mediciones de tus activos."],
  ["/activos/mantenciones", "Mantenciones", "Mantenciones preventivas, correctivas, próximas y vencidas de tus activos."],
  ["/reportes", "Centro de reportes", "Informes ambientales consolidados por obra y período de preparación."],
  ["/obras/:obraId/resumen", "Resumen de obra", "Estado ejecutivo ambiental de esta obra."],
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

// Domain key here doubles as: the CapacidadOrganizacion/aplicabilidad
// lookup key (via DOMAIN_CONFIG in operationSelectors.js), the route
// segment under `/obras/:id/operacion/`, AND the ENVIRONMENTAL_DOMAINS
// icon/color key (via its alias table for the one hyphenated case) — one
// name, three lookups, deliberately kept as the single source of truth so
// the sidebar never invents its own routes or capability keys.
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

/** The single source of navigation truth: ONE sidebar tree whose shape
 * shifts with `scope` — `{ type: "portfolio" }` or `{ type: "obra",
 * obraId }` — instead of a second, obra-specific menu bolted on below it.
 *
 * Portfolio: Inicio, Obras, Activos (expandable: vista general/flota/
 * equipos/sensores/mantenciones), Reportes, Configuración — "Control" is
 * not a portfolio-level destination: its obra-relevant parts already live
 * at `/obras/:id/control`, and its organizational parts (auditoría,
 * factores, calidad) are reachable from Configuración.
 * Obra: Resumen, Operación (expandable: 8 flujos),
 * Gestión (expandable: evidencias/problemas/cumplimiento/historial),
 * Reportes, Control, Configuración — "Obras" drops out (the context
 * selector's own "Ver todas las obras" link covers that), and Operación/
 * Gestión replace the old separate "OBRA ACTIVA" block: they are items
 * with `.children`, rendered by the SAME `GeneralNavigation` component via
 * its pre-existing expand/collapse path — never a second nav tree. */
export function getUnifiedNavigation({ preset = {}, scope } = {}) {
  const isObra = scope?.type === "obra" && Boolean(scope.obraId);
  const base = isObra ? `/obras/${scope.obraId}` : null;

  const home = {
    ...NAV_ITEMS.home,
    label: isObra ? "Resumen" : "Inicio",
    title: isObra ? "Resumen" : "Inicio",
    path: isObra ? `${base}/resumen` : "/inicio",
  };
  const reports = { ...NAV_ITEMS.reports, path: isObra ? `${base}/reportes` : "/reportes" };
  const control = { ...NAV_ITEMS.control, path: isObra ? `${base}/control` : "/gobernanza" };
  const administration = { ...NAV_ITEMS.administration, path: isObra ? `${base}/configuracion` : "/administracion" };

  if (!isObra) {
    const works = { ...NAV_ITEMS.primaryUnit };
    if (preset.unitPluralLabel) {
      works.label = preset.unitPluralLabel;
      works.title = preset.unitPluralLabel;
      works.description = `Gestiona las ${preset.unitPluralLabel.toLowerCase()} de tu organización.`;
    }
    const { path: _assetsOwnPath, ...assetsBase } = NAV_ITEMS.assets;
    const assets = { ...assetsBase, children: ASSETS_SUBNAV };
    return {
      home,
      groups: [
        { id: "general", label: "General", items: [home] },
        { id: "operation", label: "Operación", items: [works, assets] },
        { id: "outputs", label: "Salidas", items: [reports] },
        { id: "system", label: "Sistema", items: [administration] },
      ],
    };
  }

  const operation = {
    id: "operation",
    label: "Operación",
    icon: Activity,
    children: [
      ...OBRA_OPERATION_FLOWS.map((flow) => ({
        id: flow.id,
        label: flow.label,
        path: `${base}/operacion/${flow.domain}`,
        domain: flow.domain,
      })),
    ],
  };

  const management = {
    id: "management",
    label: "Gestión",
    icon: ClipboardCheck,
    children: [
      { id: "evidence", label: "Evidencias", path: `${base}/evidencias`, icon: FileCheck2 },
      { id: "problems", label: "Problemas y acciones", path: `${base}/problemas`, icon: CheckCircle2 },
      { id: "compliance", label: "Cumplimiento", path: `${base}/cumplimiento`, icon: ClipboardCheck },
      { id: "history", label: "Historial", path: `${base}/timeline`, icon: Clock3 },
    ],
  };

  return {
    home,
    groups: [
      { id: "general", label: "General", items: [home] },
      { id: "operation", label: "Operación", items: [operation] },
      { id: "management", label: "Gestión", items: [management] },
      { id: "tracking", label: "Seguimiento", items: [reports, control] },
      { id: "system", label: "Sistema", items: [administration] },
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
  const flatItems = [
    ...navigation.groups.flatMap((group) => group.items.flatMap((item) => (item.children?.length ? item.children : [item]))),
  ];
  const item = [...flatItems].sort((a, b) => b.path.length - a.path.length).find((candidate) => pathname === candidate.path || pathname.startsWith(`${candidate.path}/`));
  return item ? { title: item.title || item.label, description: item.description || "" } : { title: "Carbono Zero", description: "Gestión e inteligencia ambiental para tu organización." };
}

export const navigationForPreset = getNavigationForPreset;
