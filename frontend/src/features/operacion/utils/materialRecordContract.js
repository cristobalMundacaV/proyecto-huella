export const MATERIAL_OPERATIONAL_UNITS = [
  { value: "kg", label: "Kilogramos (kg)" }, { value: "t", label: "Toneladas (t)" },
  { value: "m3", label: "Metros cÃºbicos (m3)" }, { value: "L", label: "Litros (L)" },
  { value: "unidad", label: "Unidad" },
];

export function createMaterialMovementTechnicalCode() {
  const uniquePart = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `MATMOV-${uniquePart}`;
}

export function operationalMaterialPayload(form) {
  return { codigo: form.code.trim(), nombre: form.name.trim(), categoria: form.category.trim(), unidad_base: form.baseUnit, proveedor_fabricante: form.supplier.trim(), descripcion: form.description.trim(), especificacion_tecnica: form.technicalSpecification.trim(), activo: true };
}

export function materialActivityPayload({ workId, form, material, timestamp, code }) {
  const movement = String(form.type || "movimiento").replaceAll("_", " ");
  return { codigo: code, obra: workId, tipo: "movimiento_material", nombre: `${movement} de ${material?.nombre || "Material"}`, timestamp_inicio: timestamp };
}

export function materialEventPayload({ activityId, workId, form, timestamp }) {
  return { material: Number(form.material), actividad: activityId, obra: workId, tipo: form.type, fecha_hora: timestamp, cantidad: form.amount, unidad: form.unit, fuente: Number(form.source) };
}
