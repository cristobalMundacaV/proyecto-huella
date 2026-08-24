import {
  AlertTriangle, Bolt, Boxes, CircleGauge, Droplets, FileCheck2,
  Fuel, Hammer, LandPlot, Package, ShieldCheck, Trash2, Truck, Volume2, Wrench,
} from "lucide-react";

export const ENVIRONMENTAL_DOMAINS = {
  energia: { key: "energia", label: "Energía", icon: Bolt, text: "text-yellow-700", softBg: "bg-yellow-50", border: "border-yellow-200", accent: "from-yellow-50 via-amber-50/50 to-white" },
  agua: { key: "agua", label: "Agua", icon: Droplets, text: "text-blue-700", softBg: "bg-blue-50", border: "border-blue-200", accent: "from-blue-50 via-sky-50/50 to-white" },
  combustibles: { key: "combustibles", label: "Combustibles", icon: Fuel, text: "text-orange-700", softBg: "bg-orange-50", border: "border-orange-200", accent: "from-orange-50 via-amber-50/50 to-white" },
  maquinaria: { key: "maquinaria", label: "Maquinaria", icon: Hammer, text: "text-slate-700", softBg: "bg-slate-100", border: "border-slate-300", accent: "from-slate-100 via-slate-50 to-white" },
  transporte: { key: "transporte", label: "Transporte", icon: Truck, text: "text-indigo-700", softBg: "bg-indigo-50", border: "border-indigo-200", accent: "from-indigo-50 via-violet-50/40 to-white" },
  materiales: { key: "materiales", label: "Materiales", icon: Package, text: "text-stone-700", softBg: "bg-stone-100", border: "border-stone-300", accent: "from-stone-100 via-amber-50/45 to-white" },
  residuos: { key: "residuos", label: "Residuos", icon: Trash2, text: "text-emerald-700", softBg: "bg-emerald-50", border: "border-emerald-200", accent: "from-emerald-50 via-green-50/45 to-white" },
  ruido: { key: "ruido", label: "Ruido", icon: Volume2, text: "text-violet-700", softBg: "bg-violet-50", border: "border-violet-200", accent: "from-violet-50 via-purple-50/40 to-white" },
  hidrica_suelo: { key: "hidrica_suelo", label: "Hídrica y suelo", icon: LandPlot, text: "text-teal-700", softBg: "bg-teal-50", border: "border-teal-200", accent: "from-teal-50 via-cyan-50/40 to-white" },
  mantenimiento: { key: "mantenimiento", label: "Mantenimiento", icon: Wrench, text: "text-slate-700", softBg: "bg-slate-100", border: "border-slate-300", accent: "from-slate-100 via-blue-50/30 to-white" },
  generacion_propia: { key: "generacion_propia", label: "Generación propia", icon: Bolt, text: "text-amber-700", softBg: "bg-amber-50", border: "border-amber-200", accent: "from-amber-50 via-yellow-50 to-white" },
  cumplimiento: { key: "cumplimiento", label: "Cumplimiento", icon: ShieldCheck, text: "text-cyan-800", softBg: "bg-cyan-50", border: "border-cyan-200", accent: "from-cyan-50 via-sky-50/40 to-white" },
  problemas: { key: "problemas", label: "Problemas", icon: AlertTriangle, text: "text-rose-700", softBg: "bg-rose-50", border: "border-rose-200", accent: "from-rose-50 via-red-50/30 to-white" },
  evidencias: { key: "evidencias", label: "Evidencias", icon: FileCheck2, text: "text-teal-700", softBg: "bg-teal-50", border: "border-teal-200", accent: "from-teal-50 via-cyan-50/35 to-white" },
  operacion: { key: "operacion", label: "Operación", icon: CircleGauge, text: "text-emerald-700", softBg: "bg-emerald-50", border: "border-emerald-200", accent: "from-emerald-50 via-white to-white" },
  indicadores: { key: "indicadores", label: "Indicadores", icon: Boxes, text: "text-sky-700", softBg: "bg-sky-50", border: "border-sky-200", accent: "from-sky-50 via-white to-white" },
};

const aliases = { "hidrica-suelo": "hidrica_suelo", waterSoil: "hidrica_suelo", energy: "energia", water: "agua", fuel: "combustibles", transport: "transporte", materials: "materiales", waste: "residuos", noise: "ruido", compliance: "cumplimiento", problems: "problemas", evidence: "evidencias", operationOverview: "operacion", indicators: "indicadores" };

export function getEnvironmentalDomain(key) {
  return ENVIRONMENTAL_DOMAINS[aliases[key] || key] || null;
}

export const OPERATIONAL_DOMAIN_KEYS = ["energia", "agua", "combustibles", "transporte", "materiales", "residuos", "ruido", "hidrica_suelo"];
