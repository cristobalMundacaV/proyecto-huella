import {
    Boxes,
    Building2,
    ClipboardCheck,
    Factory,
    Leaf,
    Package,
    Settings,
    ShoppingCart,
    Truck,
    Wrench,
} from "lucide-react";

export const DEPARTMENT_PRESENTATION = {
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