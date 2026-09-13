import { Activity, ArrowLeft, BarChart3, Bot, Boxes, CheckCircle2, ClipboardCheck, Clock3, Cloud, DatabaseZap, Droplets, FileBarChart2, FileCheck2, Fuel, Gauge, Package, Settings, ShieldCheck, SlidersHorizontal, Trash2, Truck, Volume2, Zap } from "lucide-react";
import { getConfirmedWorkCapabilityKeys, hasPendingWorkApplicability, isWorkModuleConfirmed } from "@/app/workNavigationApplicability";

export const NAV_ITEMS = {
  home: { id: "home", label: "Inicio", title: "Inicio", description: "Estado ejecutivo de tu portafolio ambiental.", path: "/inicio", icon: Gauge },
  primaryUnit: { id: "primaryUnit", label: "Obras", title: "Obras", description: "Gestiona las obras de tu organización.", path: "/obras", icon: Boxes },
  reports: { id: "reports", label: "Reportes", title: "Reportes", description: "Informes ambientales consolidados por obra y período.", path: "/reportes", icon: FileBarChart2 },
  control: { id: "control", label: "Control", title: "Control", description: "Revisión, gobernanza, calidad y trazabilidad ambiental.", path: "/gobernanza", icon: ShieldCheck },
  administration: { id: "administration", label: "Configuración", title: "Configuración", description: "Organización, usuarios y parámetros de funcionamiento.", path: "/administracion", icon: Settings },
};

const PAGE_CONTEXTS = [
  ["/reportes", "Centro de reportes", "Informes ambientales por obra, período y estado de preparación."],
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

export function getNavigationForPreset(preset = {}) {
  const works = { ...NAV_ITEMS.primaryUnit };
  if (preset.unitPluralLabel) {
    works.label = preset.unitPluralLabel;
    works.title = preset.unitPluralLabel;
    works.description = `Gestiona las ${preset.unitPluralLabel.toLowerCase()} de tu organización.`;
  }
  return { home: NAV_ITEMS.home, groups: [{ id: "platform", label: "Plataforma", items: [works, NAV_ITEMS.reports, NAV_ITEMS.control, NAV_ITEMS.administration] }] };
}

const operationItems = (base) => [
  { id: "operationOverview", domain: "operacion", label: "Resumen operacional", path: `${base}/operacion`, icon: Activity },
  { id: "activityData", domain: "operacion", label: "Datos de actividad", path: `${base}/operacion/indicadores`, icon: BarChart3 },
];

export function getWorkNavigation({ obraId, applicability = [] }) {
  const base = `/obras/${obraId}`;
  const confirmed = getConfirmedWorkCapabilityKeys(applicability);
  const operation = operationItems(base).filter((item) => item.domain === "operacion" || isWorkModuleConfirmed(item, confirmed));
  return {
    exit: { id: "generalView", label: "Visión general", path: "/inicio", icon: ArrowLeft },
    groups: [
      { id: "summary", label: "Resumen", items: [{ id: "summary", label: "Resumen ejecutivo", path: `${base}/resumen`, icon: Gauge }, ...(hasPendingWorkApplicability(applicability) ? [{ id: "pendingApplicability", label: "Diagnóstico inicial", path: `${base}/diagnostico`, icon: ClipboardCheck }] : [])] },
      { id: "operation", label: "Operación", items: operation },
      { id: "management", label: "Gestión", items: [
        { id: "evidence", label: "Evidencias", path: `${base}/evidencias`, icon: FileCheck2 },
        { id: "problems", label: "Problemas y acciones", path: `${base}/problemas`, icon: CheckCircle2 },
        { id: "compliance", label: "Cumplimiento", path: `${base}/cumplimiento`, icon: ClipboardCheck },
        { id: "history", label: "Historial", path: `${base}/timeline`, icon: Clock3 },
      ] },
      { id: "control", label: "Control", items: [
        { id: "professionalReview", label: "Revisión profesional", path: "/gobernanza/revision", icon: ClipboardCheck },
        { id: "governance", label: "Gobernanza", path: "/gobernanza", icon: ShieldCheck },
        { id: "discrepancies", label: "Discrepancias", path: "/gobernanza/calidad", icon: SlidersHorizontal },
        { id: "dossiers", label: "Expedientes", path: "/gobernanza/expedientes", icon: FileCheck2 },
        { id: "quality", label: "Calidad", path: "/gobernanza/calidad", icon: ShieldCheck },
      ] },
      { id: "reports", label: "Reportes", items: [
        { id: "reports", label: "Informes", path: `${base}/reportes`, icon: BarChart3 },
        { id: "pdf", label: "PDF", path: `${base}/reportes?salida=pdf`, icon: FileBarChart2 },
        { id: "excel", label: "Excel", path: `${base}/reportes?salida=excel`, icon: DatabaseZap },
        { id: "charts", label: "Gráficos", path: `${base}/reportes#graficos`, icon: BarChart3 },
      ] },
      { id: "configuration", label: "Configuración", items: [
        { id: "environmentalProfile", label: "Perfil ambiental", path: `${base}/diagnostico`, icon: Gauge },
        { id: "scopes", label: "Ámbitos", path: "/administracion/ambiental", icon: Boxes },
        { id: "factors", label: "Factores", path: "/gobernanza/factores", icon: SlidersHorizontal },
        { id: "methodologies", label: "Metodologías", path: "/gobernanza/factores", icon: Bot },
        { id: "parameters", label: "Parámetros", path: "/administracion/calculo", icon: Settings },
      ] },
    ],
  };
}

export function getPageContext(pathname, preset) {
  const exact = [...PAGE_CONTEXTS].sort((a, b) => b.pattern.length - a.pattern.length).find((item) => matchesPattern(pathname, item.pattern));
  if (exact) return exact;
  const navigation = getNavigationForPreset(preset);
  const item = [navigation.home, ...navigation.groups.flatMap((group) => group.items)].sort((a, b) => b.path.length - a.path.length).find((candidate) => pathname === candidate.path || pathname.startsWith(`${candidate.path}/`));
  return item ? { title: item.title || item.label, description: item.description || "" } : { title: "Carbono Zero", description: "Gestión e inteligencia ambiental para tu organización." };
}

export const navigationForPreset = getNavigationForPreset;
