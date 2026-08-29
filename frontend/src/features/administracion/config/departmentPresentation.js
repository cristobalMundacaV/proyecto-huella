import {
    BriefcaseBusiness,
    Boxes,
    Building2,
    ClipboardCheck,
    ClipboardList,
    Factory,
    HardHat,
    Leaf,
    Package,
    Settings,
    ShieldAlert,
    ShoppingCart,
    Truck,
    Wrench,
} from "lucide-react";

const style = (icon, headerClass, iconClass) => ({
    icon,
    headerClass,
    iconClass,
});

export const DEPARTMENT_PRESENTATION = {
    administracion: style(
        BriefcaseBusiness,
        "bg-slate-50 border-slate-200",
        "bg-slate-200/70 text-slate-700",
    ),
    compras_adquisiciones: style(
        ShoppingCart,
        "bg-zinc-50 border-zinc-200",
        "bg-zinc-200/70 text-zinc-700",
    ),
    maquinaria_equipos: style(
        Settings,
        "bg-stone-50 border-stone-200",
        "bg-stone-200/70 text-stone-700",
    ),
    medio_ambiente_sostenibilidad: style(
        Leaf,
        "bg-emerald-50 border-emerald-200",
        "bg-emerald-100 text-emerald-700",
    ),
    oficina_tecnica: style(
        ClipboardList,
        "bg-blue-50 border-blue-200",
        "bg-blue-100 text-blue-700",
    ),
    prevencion_riesgos_hse: style(
        ShieldAlert,
        "bg-red-50 border-red-200",
        "bg-red-100 text-red-700",
    ),
    terreno_supervision: style(
        HardHat,
        "bg-cyan-50 border-cyan-200",
        "bg-cyan-100 text-cyan-700",
    ),
    medio_ambiente: {
        icon: Leaf,
        headerClass:
            "bg-emerald-50 border-emerald-200",
        iconClass:
            "bg-emerald-100 text-emerald-700",
    },

    maquinaria_operaciones: {
        icon: Settings,
        headerClass:
            "bg-blue-50 border-blue-200",
        iconClass:
            "bg-blue-100 text-blue-700",
    },

    logistica_transporte: {
        icon: Truck,
        headerClass:
            "bg-violet-50 border-violet-200",
        iconClass:
            "bg-violet-100 text-violet-700",
    },

    bodega: {
        icon: Package,
        headerClass:
            "bg-amber-50 border-amber-200",
        iconClass:
            "bg-amber-100 text-amber-700",
    },

    administracion_compras: {
        icon: ShoppingCart,
        headerClass:
            "bg-slate-50 border-slate-200",
        iconClass:
            "bg-slate-100 text-slate-700",
    },

    gestion_obra: {
        icon: Building2,
        headerClass:
            "bg-orange-50 border-orange-200",
        iconClass:
            "bg-orange-100 text-orange-700",
    },

    mantenimiento: {
        icon: Wrench,
        headerClass:
            "bg-indigo-50 border-indigo-200",
        iconClass:
            "bg-indigo-100 text-indigo-700",
    },

    produccion: {
        icon: Factory,
        headerClass:
            "bg-cyan-50 border-cyan-200",
        iconClass:
            "bg-cyan-100 text-cyan-700",
    },

    calidad_laboratorio: {
        icon: ClipboardCheck,
        headerClass:
            "bg-teal-50 border-teal-200",
        iconClass:
            "bg-teal-100 text-teal-700",
    },

    otro: {
        icon: Boxes,
        headerClass:
            "bg-gray-50 border-gray-200",
        iconClass:
            "bg-gray-100 text-gray-700",
    },
};

export const DEPARTMENT_TYPE_OPTIONS = [
    ["administracion_compras", "Administración y compras"],
    ["bodega", "Bodega"],
    ["logistica_transporte", "Logística y transporte"],
    ["maquinaria_operaciones", "Maquinaria y operaciones"],
    ["medio_ambiente", "Medio ambiente"],
    ["gestion_obra", "Gestión de obra"],
    ["mantenimiento", "Mantenimiento"],
    ["produccion", "Producción"],
    ["calidad_laboratorio", "Calidad y laboratorio"],
    ["otro", "Otro"],
];
