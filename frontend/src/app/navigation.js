import {
  BarChart3, Bot, Boxes, Building2, CheckCircle2, ClipboardCheck,
  Database, DatabaseZap, Factory, FileCheck2, LayoutDashboard,
  Settings, ShieldCheck, Truck, UsersRound,
} from "lucide-react";

export const navigationGroups = [
  { label: "Inicio", items: [{ label: "Inicio", path: "/inicio", icon: LayoutDashboard }] },
  { label: "Obras", items: [{ label: "Obras", path: "/obras", icon: Boxes }] },
  { label: "Datos", items: [
    { label: "Importaciones", path: "/datos/importaciones", icon: DatabaseZap },
    { label: "Evidencias", path: "/datos/evidencias", icon: FileCheck2 },
  ] },
  { label: "Operación", items: [
    { label: "Activos", path: "/operacion/activos", icon: Truck },
    { label: "Sensores", path: "/operacion/sensores", icon: DatabaseZap },
  ] },
  { label: "Inteligencia", items: [
    { label: "Inteligencia", path: "/inteligencia", icon: ShieldCheck },
    { label: "Problemas y mejora", path: "/inteligencia/problemas", icon: CheckCircle2 },
    { label: "Copiloto", path: "/inteligencia/copiloto", icon: Bot },
  ] },
  { label: "Gobernanza", items: [
    { label: "Gobernanza", path: "/gobernanza", icon: ShieldCheck },
    { label: "Revisión profesional", path: "/gobernanza/revision", icon: ClipboardCheck },
    { label: "Expedientes", path: "/gobernanza/expedientes", icon: FileCheck2 },
    { label: "Calidad", path: "/gobernanza/calidad", icon: CheckCircle2 },
    { label: "Factores", path: "/gobernanza/factores", icon: Database },
    { label: "Auditoría", path: "/gobernanza/auditoria", icon: BarChart3 },
  ] },
  { label: "Administración", items: [
    { label: "Administración", path: "/administracion", icon: Settings },
    { label: "Organización", path: "/administracion/organizacion", icon: Building2 },
    { label: "Usuarios", path: "/administracion/usuarios", icon: UsersRound },
    { label: "Configuración", path: "/administracion/configuracion", icon: Settings },
    { label: "Diagnóstico", path: "/administracion/diagnostico", icon: ClipboardCheck },
    { label: "Estructura", path: "/administracion/estructura", icon: Factory },
  ] },
];

export function navigationForPreset(preset) {
  const sectorItems = (preset?.navigationExtensions || []).map((item) => ({
    ...item,
    icon: Factory,
  }));
  return sectorItems.length
    ? [...navigationGroups, { label: preset.name, items: sectorItems }]
    : navigationGroups;
}
