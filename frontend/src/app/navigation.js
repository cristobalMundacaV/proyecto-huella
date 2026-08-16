import { Activity, Bot, Boxes, CheckCircle2, ClipboardCheck, DatabaseZap, Factory, FileCheck2, Flame, Layers3, LayoutDashboard, Recycle, Settings, ShieldCheck, Trees, Truck } from "lucide-react";

export const NAV_ITEMS = {
  home: { id: "home", label: "Inicio", path: "/inicio", icon: LayoutDashboard },
  primaryUnit: { id: "primaryUnit", path: "/obras", icon: Boxes },
  assets: { id: "assets", label: "Activos", path: "/operacion/activos", icon: Truck },
  sensors: { id: "sensors", label: "Sensores", path: "/operacion/sensores", icon: Activity },
  evidence: { id: "evidence", label: "Evidencias", path: "/datos/evidencias", icon: FileCheck2 },
  imports: { id: "imports", label: "Importaciones", path: "/datos/importaciones", icon: DatabaseZap },
  intelligence: { id: "intelligence", label: "Inteligencia", path: "/inteligencia", icon: Activity },
  improvement: { id: "improvement", label: "Problemas y acciones", path: "/inteligencia/problemas", icon: CheckCircle2 },
  copilot: { id: "copilot", label: "Copiloto", path: "/inteligencia/copiloto", icon: Bot },
  governance: { id: "governance", label: "Gobernanza", path: "/gobernanza", icon: ShieldCheck },
  professionalReview: { id: "professionalReview", label: "Revisión profesional", path: "/gobernanza/revision", icon: ClipboardCheck },
  administration: { id: "administration", label: "Administración", path: "/administracion", icon: Settings },
};

const GROUPS = {
  operation: "Mi operación",
  data: "Datos",
  environmental: "Gestión ambiental",
  control: "Control",
  configuration: "Configuración",
};

const defaultProfile = {
  operation: ["primaryUnit", "assets", "sensors"],
  data: ["evidence", "imports"],
  environmental: ["intelligence", "improvement", "copilot"],
  control: ["governance", "professionalReview"],
  configuration: ["administration"],
};

function capability(id, preset) {
  const item = NAV_ITEMS[id];
  if (!item) return null;
  return id === "primaryUnit" ? { ...item, label: preset.unitPluralLabel } : item;
}

function sectorOperations(preset) {
  if (!preset.navigationExtensions?.length) return null;
  return {
    id: "sectorOperations",
    label: preset.navigationProfile?.processesLabel || `${preset.processPluralLabel} de ${preset.unitLabel.toLowerCase()}`,
    icon: Factory,
    children: preset.navigationExtensions.map((item, index) => ({ ...item, id: `sector-${index}`, icon: sectorIcon(item.path) })),
  };
}

function sectorIcon(path) {
  if (path.includes("recepcion")) return Trees;
  if (path.includes("secado") || path.includes("energia")) return Flame;
  if (path.includes("transporte")) return Truck;
  if (path.includes("residuos")) return Recycle;
  if (path.includes("lotes")) return Layers3;
  return Factory;
}

export function getNavigationForPreset(preset) {
  const selected = preset || {};
  const profile = { ...defaultProfile, ...(selected.navigationProfile || {}) };
  const groups = Object.entries(GROUPS).map(([id, label]) => ({
    id,
    label,
    items: (profile[id] || []).map((itemId) => itemId === "sectorOperations" ? sectorOperations(selected) : capability(itemId, selected)).filter(Boolean),
  })).filter((group) => group.items.length);
  return { home: NAV_ITEMS.home, groups };
}

export const navigationForPreset = getNavigationForPreset;
