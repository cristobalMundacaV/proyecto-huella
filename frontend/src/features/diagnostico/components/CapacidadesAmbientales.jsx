import { useLayoutEffect, useRef, useState } from "react";

import { Alert, Select, StatusBadge } from "@/shared/ui";
import { updateCapacidad } from "../api/diagnosticoApi";

const states = [
  ["pendiente_diagnostico", "Pendiente de diagnóstico"],
  ["aplica", "Aplica"],
  ["no_aplica", "No aplica"],
  ["sin_datos", "Sin datos"],
  ["construyendo_linea_base", "Construyendo línea base"],
  ["operativa", "Operativa"],
];
const tone = (value) => value === "operativa" ? "success" : ["pendiente_diagnostico", "sin_datos", "construyendo_linea_base"].includes(value) ? "warning" : "neutral";

export default function CapacidadesAmbientales({ organizacionId, capacidades = [], onChange, readOnly = false }) {
  const [error, setError] = useState("");
  const [savingId, setSavingId] = useState(null);
  const organizationRef = useRef(organizacionId);

  useLayoutEffect(() => {
    organizationRef.current = organizacionId;
  }, [organizacionId]);

  async function change(item, estado) {
    const organizationId = organizacionId;
    setSavingId(item.id);
    setError("");
    try {
      await updateCapacidad(organizationId, item.id, { estado });
      if (String(organizationRef.current) !== String(organizationId)) return;
      await onChange?.();
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo actualizar la aplicabilidad.");
    } finally {
      setSavingId(null);
    }
  }

  return <div className="space-y-3">
    {error && <Alert tone="danger">{error}</Alert>}
    <div className="grid gap-3 md:grid-cols-2">{capacidades.map((item) => (
      <div key={item.id} className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h3 className="font-black">{item.capacidad?.nombre || "Capacidad"}</h3><p className="mt-1 text-xs text-[var(--text-muted)]">{item.recomendada_por_preset ? "Sugerida por el perfil de operación" : "Configurada para esta organización"}</p></div>
          <StatusBadge tone={tone(item.estado)}>{states.find(([value]) => value === item.estado)?.[1] || item.estado || "Sin datos"}</StatusBadge>
        </div>
        {!readOnly && <div className="mt-4"><Select label={`Aplicabilidad de ${item.capacidad?.nombre || "capacidad"}`} value={item.estado} disabled={savingId === item.id} onChange={(event) => change(item, event.target.value)}>
          {states.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </Select></div>}
      </div>
    ))}</div>
  </div>;
}
