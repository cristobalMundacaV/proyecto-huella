export const EMPTY_VEHICLE = Object.freeze({
  patente: "",
  marca: "",
  modelo: "",
  anio: null,
  tipo_vehiculo: "",
  combustible: "",
  capacidad_carga: null,
  unidad_capacidad_carga: "",
  numero_ejes: null,
});

const optionalNumber = (value) => value === "" || value == null ? null : value;

export function assetDraft(item = {}) {
  return {
    codigo: "",
    nombre: "",
    tipo: "vehiculo",
    estado: "operativo",
    descripcion: "",
    ...item,
    vehiculo: { ...EMPTY_VEHICLE, ...(item.vehiculo || {}) },
  };
}

export function assetPayload(draft) {
  const payload = {
    codigo: draft.codigo,
    nombre: draft.nombre,
    tipo: draft.tipo,
    estado: draft.estado,
    descripcion: draft.descripcion || "",
  };
  if (draft.tipo === "vehiculo") {
    payload.vehiculo = {
      ...EMPTY_VEHICLE,
      ...(draft.vehiculo || {}),
      anio: optionalNumber(draft.vehiculo?.anio),
      capacidad_carga: optionalNumber(draft.vehiculo?.capacidad_carga),
      numero_ejes: optionalNumber(draft.vehiculo?.numero_ejes),
    };
    delete payload.vehiculo.id;
  }
  return payload;
}

export function selectableVehicleAssets(items = []) {
  return items.filter(
    (item) => item.tipo === "vehiculo" && Boolean(item.vehiculo?.id),
  );
}
