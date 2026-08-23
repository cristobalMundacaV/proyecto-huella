import {
  Activity,
  Bot,
  Boxes,
  ArrowLeft,
  BarChart3,
  Clock3,
  FileCheck2,
  Gauge,
  TriangleAlert,
  CheckCircle2,
  ClipboardCheck,
  DatabaseZap,
  Factory,
  Flame,
  Layers3,
  LayoutDashboard,
  Droplets,
  Fuel,
  LandPlot,
  Package,
  Trash2,
  Volume2,
  Zap,
  Recycle,
  Settings,
  ShieldCheck,
  Trees,
  Truck,
} from "lucide-react";

export const NAV_ITEMS = {
  home: {
    id: "home",
    label: "Inicio",
    title: "Inicio",
    description: "Resumen ejecutivo de tu operación ambiental.",
    path: "/inicio",
    icon: LayoutDashboard,
  },

  primaryUnit: {
    id: "primaryUnit",
    title: "Unidades operacionales",
    description: "Gestiona las unidades ambientales de tu organización.",
    path: "/obras",
    icon: Boxes,
  },

  assets: {
    id: "assets",
    label: "Activos",
    title: "Activos",
    description: "Equipos y activos vinculados a tu operación ambiental.",
    path: "/operacion/activos",
    icon: Truck,
  },

  sensors: {
    id: "sensors",
    label: "Sensores",
    title: "Sensores",
    description: "Monitorea dispositivos y lecturas de tu operación.",
    path: "/operacion/sensores",
    icon: Activity,
  },

  evidence: {
    id: "evidence",
    label: "Evidencias",
    title: "Evidencias",
    description: "Documentos y antecedentes que respaldan la trazabilidad ambiental.",
    path: "/datos/evidencias",
    icon: FileCheck2,
  },

  imports: {
    id: "imports",
    label: "Importaciones",
    title: "Importaciones",
    description: "Incorpora información operacional desde archivos y fuentes externas.",
    path: "/datos/importaciones",
    icon: DatabaseZap,
  },

  intelligence: {
    id: "intelligence",
    label: "Inteligencia",
    title: "Inteligencia",
    description: "Señales y análisis que ayudan a identificar dónde profundizar.",
    path: "/inteligencia",
    icon: Activity,
  },

  improvement: {
    id: "improvement",
    label: "Problemas y acciones",
    title: "Problemas y acciones",
    description: "Gestiona situaciones ambientales desde su detección hasta verificar el resultado.",
    path: "/inteligencia/problemas",
    icon: CheckCircle2,
  },

  copilot: {
    id: "copilot",
    label: "Copiloto",
    title: "Copiloto ambiental",
    description: "Consulta el contexto de un problema y prepara decisiones mejor informadas.",
    path: "/inteligencia/copiloto",
    icon: Bot,
  },

  governance: {
    id: "governance",
    label: "Gobernanza",
    title: "Gobernanza",
    description: "Controla revisiones, discrepancias y decisiones ambientales formales.",
    path: "/gobernanza",
    icon: ShieldCheck,
  },

  professionalReview: {
    id: "professionalReview",
    label: "Revisión profesional",
    title: "Revisión profesional",
    description: "Elementos que requieren evaluación y decisión profesional.",
    path: "/gobernanza/revision",
    icon: ClipboardCheck,
  },

  administration: {
    id: "administration",
    label: "Configuración",
    title: "Configuración",
    description: "Gestiona la organización, sus usuarios y preferencias de funcionamiento.",
    path: "/administracion",
    icon: Settings,
  },
};

const PAGE_CONTEXTS = [
  {
    pattern: "/datos",
    title: "Datos",
    description: "Revisa qué información tienes, qué falta y qué requiere atención.",
  },

  {
    pattern: "/datos/evidencias/:evidenceId",
    title: "Detalle de evidencia",
    description: "Revisa el documento, su contexto, versiones y trazabilidad.",
  },

  {
    pattern: "/datos/importaciones/:processId",
    title: "Detalle de importación",
    description: "Revisa el estado, progreso y resultado de la importación.",
  },

  {
    pattern: "/operacion/sensores/:sensorId",
    title: "Detalle de sensor",
    description: "Revisa el dispositivo, sus lecturas y su trazabilidad operacional.",
  },

  {
    pattern: "/obras/:obraId/resumen",
    title: "Resumen de unidad",
    description: "Estado ambiental y señales principales de esta unidad.",
  },


  {
    pattern: "/obras/:obraId/operacion",
    title: "Operación",
    description: "Revisa qué está ocurriendo físicamente en esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/energia",
    title: "Energía",
    description: "Consumos y registros energéticos asociados a esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/agua",
    title: "Agua",
    description: "Consumos y registros hídricos asociados a esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/combustibles",
    title: "Combustibles",
    description: "Uso de combustibles registrado en esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/transporte",
    title: "Transporte",
    description: "Movimientos, distancias y carga registrados en esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/materiales",
    title: "Materiales",
    description: "Movimientos y balances de materiales registrados en esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/residuos",
    title: "Residuos",
    description: "Registros de residuos asociados a la operación de esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/ruido",
    title: "Ruido",
    description: "Mediciones y registros acústicos asociados a esta unidad.",
  },

  {
    pattern: "/obras/:obraId/operacion/hidrica-suelo",
    title: "Hídrica y suelo",
    description: "Condiciones y registros ambientales vinculados a agua y suelo.",
  },

  {
    pattern: "/obras/:obraId/indicadores",
    title: "Indicadores",
    description: "Indicadores ambientales y operacionales de esta unidad.",
  },

  {
    pattern: "/obras/:obraId/problemas/:problemId",
    title: "Detalle de problema",
    description: "Revisa el problema, su acción actual, seguimiento y resultado.",
  },

  {
    pattern: "/obras/:obraId/problemas",
    title: "Problemas",
    description: "Situaciones ambientales gestionadas dentro de esta unidad.",
  },

  {
    pattern: "/obras/:obraId/evidencias",
    title: "Evidencias de la unidad",
    description: "Antecedentes y documentos vinculados a esta unidad.",
  },

  {
    pattern: "/obras/:obraId/timeline",
    title: "Historial",
    description: "Actividad y cambios registrados a lo largo del tiempo.",
  },

  {
    pattern: "/inteligencia/problemas/:problemId",
    title: "Detalle de problema",
    description: "Revisa qué se intenta resolver, qué acción se tomó y cuál fue el resultado.",
  },

  {
    pattern: "/gobernanza/expedientes/:dossierId",
    title: "Detalle de expediente",
    description: "Revisa el alcance, antecedentes y decisiones asociadas al expediente.",
  },

  {
    pattern: "/gobernanza/expedientes",
    title: "Expedientes",
    description: "Antecedentes ambientales preparados para control, revisión y uso formal.",
  },

  {
    pattern: "/gobernanza/factores",
    title: "Factores y metodologías",
    description: "Consulta referencias y metodologías utilizadas por el cálculo gobernado.",
  },

  {
    pattern: "/gobernanza/calidad",
    title: "Calidad y discrepancias",
    description: "Revisa datos que presentan diferencias o requieren validación.",
  },

  {
    pattern: "/gobernanza/auditoria",
    title: "Auditoría",
    description: "Historial verificable de acciones y decisiones gobernadas.",
  },

  {
    pattern: "/gobernanza/conocimiento",
    title: "Conocimiento",
    description: "Conocimiento ambiental validado y disponible para la plataforma.",
  },

  {
    pattern: "/gobernanza/informes",
    title: "Informes gobernados",
    description: "Expedientes e informes preparados a partir de antecedentes controlados.",
  },

  {
    pattern: "/administracion/organizacion",
    title: "Organización",
    description: "Administra la identidad y configuración general de tu organización.",
  },

  {
    pattern: "/administracion/usuarios",
    title: "Usuarios y roles",
    description: "Gestiona quién tiene acceso y qué rol posee dentro de la organización.",
  },

  {
    pattern: "/administracion/configuracion",
    title: "Preferencias",
    description: "Configura preferencias operativas, documentales y de presentación.",
  },

  {
    pattern: "/administracion/diagnostico",
    title: "Diagnóstico de contexto",
    description: "Define el contexto organizacional que determina qué aplica a tu operación.",
  },

  {
    pattern: "/administracion/estructura",
    title: "Estructura operacional",
    description: "Organiza las etapas y componentes que estructuran tu operación.",
  },

  {
    pattern: "/operacion/recepcion-trozas",
    title: "Recepción",
    description: "Registra y revisa la recepción de materia prima de la operación.",
  },

  {
    pattern: "/operacion/produccion",
    title: "Producción",
    description: "Revisa la actividad productiva registrada en la operación.",
  },

  {
    pattern: "/operacion/secado",
    title: "Secado",
    description: "Monitorea los procesos y registros asociados al secado.",
  },

  {
    pattern: "/operacion/energia",
    title: "Energía",
    description: "Revisa el consumo energético asociado al proceso productivo.",
  },

  {
    pattern: "/operacion/transporte-forestal",
    title: "Transporte forestal",
    description: "Gestiona los movimientos y transporte asociados a la operación forestal.",
  },

  {
    pattern: "/operacion/residuos-subproductos",
    title: "Residuos y subproductos",
    description: "Revisa residuos, subproductos y movimientos derivados de la operación.",
  },

  {
    pattern: "/operacion/lotes-forestales",
    title: "Lotes",
    description: "Consulta los lotes y su trazabilidad dentro de la operación.",
  },
];

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

  if (id === "primaryUnit") {
    return {
      ...item,
      label: preset.unitPluralLabel,
      title: preset.unitPluralLabel,
      description: `Gestiona las ${preset.unitPluralLabel.toLowerCase()} de tu organización.`,
    };
  }

  return item;
}

function sectorOperations(preset) {
  if (!preset.navigationExtensions?.length) return null;

  return {
    id: "sectorOperations",
    label:
      preset.navigationProfile?.processesLabel ||
      `${preset.processPluralLabel} de ${preset.unitLabel.toLowerCase()}`,
    icon: Factory,
    children: preset.navigationExtensions.map((item, index) => ({
      ...item,
      id: `sector-${index}`,
      icon: sectorIcon(item.path),
    })),
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

function matchesPattern(pathname, pattern) {
  const pathnameParts = pathname
    .split("/")
    .filter(Boolean);

  const patternParts = pattern
    .split("/")
    .filter(Boolean);

  if (pathnameParts.length !== patternParts.length) {
    return false;
  }

  return patternParts.every((part, index) => {
    if (part.startsWith(":")) return true;

    return part === pathnameParts[index];
  });
}

export function getNavigationForPreset(preset) {
  const selected = preset || {};

  const profile = {
    ...defaultProfile,
    ...(selected.navigationProfile || {}),
  };

  const groups = Object.entries(GROUPS)
    .map(([id, label]) => ({
      id,
      label,
      items: (profile[id] || [])
        .map(itemId =>
          itemId === "sectorOperations"
            ? sectorOperations(selected)
            : capability(itemId, selected)
        )
        .filter(Boolean),
    }))
    .filter(group => group.items.length);

  return {
    home: NAV_ITEMS.home,
    groups,
  };
}

export function getWorkNavigation({
  obraId,
  applicability = [],
}) {
  const base =
    `/obras/${obraId}`;
  const visibleCapabilities = new Set(
    applicability
      .filter((item) => ["aplica", "sin_datos"].includes(item?.estado_obra))
      .map((item) => item?.clave)
      .filter(Boolean),
  );

  return {
    exit: {
      id: "generalView",
      label: "Visión general",
      path: "/inicio",
      icon: ArrowLeft,
    },

    groups: [
      {
        id: "work",
        label: "Obra",
        items: [
          {
            id: "summary",
            label: "Resumen",
            path: `${base}/resumen`,
            icon: Gauge,
          },
        ],
      },

      {
        id: "operation",
        label: "Operación",
        items: [
          {
            id: "operationOverview",
            domain: "operacion",
            label: "Resumen operacional",
            path: `${base}/operacion`,
            icon: Activity,
          },

          {
            id: "energy",
            domain: "energia",
            label: "Energía",
            path: `${base}/operacion/energia`,
            icon: Zap,
          },

          {
            id: "water",
            domain: "agua",
            label: "Agua",
            path: `${base}/operacion/agua`,
            icon: Droplets,
          },

          {
            id: "fuel",
            domain: "combustibles",
            label: "Combustibles",
            path: `${base}/operacion/combustibles`,
            icon: Fuel,
          },

          {
            id: "transport",
            domain: "transporte",
            label: "Transporte",
            path: `${base}/operacion/transporte`,
            icon: Truck,
          },

          {
            id: "materials",
            domain: "materiales",
            label: "Materiales",
            path: `${base}/operacion/materiales`,
            icon: Package,
          },

          {
            id: "waste",
            domain: "residuos",
            label: "Residuos",
            path: `${base}/operacion/residuos`,
            icon: Trash2,
          },

          {
            id: "noise",
            domain: "ruido",
            label: "Ruido",
            path: `${base}/operacion/ruido`,
            icon: Volume2,
          },

          {
            id: "waterSoil",
            domain: "hidrica_suelo",
            capability: "gestion_hidrica_suelo",
            label: "Hídrica y suelo",
            path: `${base}/operacion/hidrica-suelo`,
            icon: LandPlot,
          },

          {
            id: "indicators",
            domain: "indicadores",
            label: "Indicadores",
            path: `${base}/indicadores`,
            icon: BarChart3,
          },
          {
            id: "compliance",
            domain: "cumplimiento",
            label: "Cumplimiento",
            path: `${base}/cumplimiento`,
            icon: BarChart3,
          },
        ].filter((item) => !item.domain || ["operacion", "indicadores", "cumplimiento"].includes(item.domain) || visibleCapabilities.has(item.capability || item.domain)),
      },

      {
        id: "environmental",
        label: "Gestión ambiental",
        items: [
          {
            id: "problems",
            domain: "problemas",
            label: "Problemas",
            path: `${base}/problemas`,
            icon: TriangleAlert,
          },

          {
            id: "evidence",
            domain: "evidencias",
            label: "Evidencias",
            path: `${base}/evidencias`,
            icon: FileCheck2,
          },

          {
            id: "history",
            label: "Historial",
            path: `${base}/timeline`,
            icon: Clock3,
          },
        ],
      },
    ],
  };
}

export function getPageContext(pathname, preset) {
  const navigation = getNavigationForPreset(preset);

  const navigationItems = [
    navigation.home,
    ...navigation.groups.flatMap(group =>
      group.items.flatMap(item =>
        item.children?.length
          ? item.children
          : [item]
      )
    ),
  ].filter(Boolean);

  const exactPageContext = PAGE_CONTEXTS
    .sort(
      (a, b) =>
        b.pattern.split("/").length -
        a.pattern.split("/").length
    )
    .find(item =>
      matchesPattern(pathname, item.pattern)
    );

  if (exactPageContext) {
    return exactPageContext;
  }

  const navigationItem = [...navigationItems]
    .filter(item => item.path)
    .sort(
      (a, b) =>
        b.path.length -
        a.path.length
    )
    .find(item =>
      pathname === item.path ||
      pathname.startsWith(`${item.path}/`)
    );

  if (navigationItem) {
    return {
      title:
        navigationItem.title ||
        navigationItem.label,
      description:
        navigationItem.description ||
        "",
    };
  }

  return {
    title: "Carbono Zero",
    description:
      "Gestión e inteligencia ambiental para tu organización.",
  };
}

export const navigationForPreset =
  getNavigationForPreset;
