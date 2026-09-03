export function createJourneyTechnicalCode() {
  const uniquePart = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `VIAJE-${uniquePart}`;
}

export function transportActivityPayload({ workId, form, timestamp, code }) {
  return {
    obra: workId,
    tipo: "transporte",
    codigo: code,
    nombre: `Viaje ${form.origin.trim()} → ${form.destination.trim()}`,
    timestamp_inicio: timestamp,
  };
}

export function transportJourneyPayload({ activityId, form, timestamp, code }) {
  return {
    actividad: activityId,
    codigo: code,
    vehiculo: Number(form.vehicle),
    origen_nombre: form.origin.trim(),
    destino_nombre: form.destination.trim(),
    fecha_salida: timestamp,
    distancia: form.distance,
    carga: form.load || null,
    combustible: form.fuel || null,
    fuente: Number(form.source),
    estado_carga: form.loadState,
    tipo_trayecto: form.tripType,
    estado: "completado",
  };
}
