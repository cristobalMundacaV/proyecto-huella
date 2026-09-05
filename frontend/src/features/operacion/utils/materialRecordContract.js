export const MATERIAL_OPERATIONAL_UNITS = [
  { value: "kg", label: "Kilogramos (kg)" }, { value: "t", label: "Toneladas (t)" },
  { value: "m3", label: "Metros c\u00fabicos (m\u00b3)" }, { value: "L", label: "Litros (L)" },
  { value: "unidad", label: "Unidades" },
];

export const MATERIAL_OPERATIONAL_CATEGORIES = [
  { value: "cemento", label: "Cemento" }, { value: "hormigon", label: "Hormig\u00f3n" },
  { value: "acero", label: "Acero" }, { value: "madera", label: "Madera" },
  { value: "aridos", label: "\u00c1ridos" }, { value: "ladrillos_bloques", label: "Ladrillos y bloques" },
  { value: "yeso_placas", label: "Yeso y placas" }, { value: "vidrio", label: "Vidrio" },
  { value: "aluminio_otros_metales", label: "Aluminio y otros metales" },
  { value: "aislacion", label: "Aislaci\u00f3n" },
  { value: "pinturas_revestimientos", label: "Pinturas y revestimientos" },
  { value: "plasticos_pvc", label: "Pl\u00e1sticos / PVC" }, { value: "tuberias", label: "Tuber\u00edas" },
  { value: "asfalto", label: "Asfalto" }, { value: "prefabricados", label: "Prefabricados" },
  { value: "otros", label: "Otros" },
];

export function createMaterialMovementTechnicalCode() {
  const uniquePart = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `MATMOV-${uniquePart}`;
}

export function operationalMaterialPayload(form) {
  return { nombre: form.name.trim(), categoria: form.category, unidad_base: form.baseUnit, proveedor_fabricante: form.supplier.trim(), descripcion: form.description.trim(), activo: true };
}

export function materialActivityPayload({ workId, form, material, timestamp, code }) {
  const movement = String(form.type || "movimiento").replaceAll("_", " ");
  return { codigo: code, obra: workId, tipo: "movimiento_material", nombre: `${movement} de ${material?.nombre || "Material"}`, timestamp_inicio: timestamp };
}

export function materialEventPayload({ activityId, workId, form, timestamp }) {
  return { material: Number(form.material), actividad: activityId, obra: workId, tipo: form.type, fecha_hora: timestamp, cantidad: form.amount, unidad: form.unit, fuente: Number(form.source) };
}
