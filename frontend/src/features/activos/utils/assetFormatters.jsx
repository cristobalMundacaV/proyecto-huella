const TYPE_LABELS = {
    vehiculo: "Vehículo",
    maquinaria: "Maquinaria",
    equipo: "Equipo",
    medidor: "Medidor",
    infraestructura: "Infraestructura",
    otro: "Otro",
};

const STATUS_LABELS = {
    operativo: "Operativo",
    requiere_revision: "Requiere revisión",
    fuera_servicio: "Fuera de servicio",
    retirado: "Retirado",
};

function humanizeFallback(value) {
    return String(value || "")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function assetTypeLabel(value) {
    return TYPE_LABELS[value] || humanizeFallback(value) || "Sin tipo";
}

export function assetStatusLabel(value) {
    return STATUS_LABELS[value] || humanizeFallback(value) || "Sin estado";
}

export const ASSET_TYPE_OPTIONS = [
    "vehiculo",
    "maquinaria",
    "equipo",
    "medidor",
    "infraestructura",
    "otro",
];

export const ASSET_STATUS_OPTIONS = [
    "operativo",
    "requiere_revision",
    "fuera_servicio",
    "retirado",
];