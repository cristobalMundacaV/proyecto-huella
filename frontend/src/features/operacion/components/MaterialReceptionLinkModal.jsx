import { useEffect, useMemo, useState } from "react";
import { Link2 } from "lucide-react";
import Toast from "@/shared/components/Toast";
import { Alert, Button, Modal, Select } from "@/shared/ui";
import { humanizeApiError } from "@/shared/utils/apiErrors";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import { updateMaterialEvent } from "../api/materialsApi";
import { compatibleMaterialReceptions } from "../utils/materialRecordContract";

function receptionLabel(reception) {
  const quantity = reception.cantidad_detalle;
  const source = quantity?.fuente_detalle?.nombre || "Fuente no informada";
  return `${formatDateTime(reception.fecha_hora)} · Recepción ${formatNumber(quantity?.valor_numerico)} ${quantity?.unidad || ""} · ${source}`;
}

export default function MaterialReceptionLinkModal({ open, onClose, organizationId, workId, event, events, onLinked }) {
  const candidates = useMemo(() => event ? compatibleMaterialReceptions(events, {
    materialId: event.material,
    workId,
    unit: event.cantidad_detalle?.unidad,
    timestamp: event.fecha_hora,
  }) : [], [event, events, workId]);
  const [selected, setSelected] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!open) return;
    setSelected(candidates.length === 1 ? String(candidates[0].id) : "");
    setError("");
  }, [open, candidates]);

  async function submit(submitEvent) {
    submitEvent.preventDefault();
    if (!selected) return;
    setSaving(true); setError("");
    try {
      await updateMaterialEvent(organizationId, event.id, { evento_origen: Number(selected) });
      setToast({ id: Date.now(), tone: "success", message: "Recepción vinculada", subtitle: "La trazabilidad del movimiento fue actualizada." });
      onClose(); await onLinked?.();
    } catch (requestError) {
      const message = humanizeApiError(requestError, "No fue posible vincular la recepción.");
      setError(message); setToast({ id: Date.now(), tone: "error", message: "No pudimos vincular la recepción", subtitle: message });
    } finally { setSaving(false); }
  }

  return <>
    <Toast {...toast} toastKey={toast?.id} onClose={() => setToast(null)} />
    <Modal open={open} onClose={onClose} eyebrow="TRAZABILIDAD OPERACIONAL" icon={Link2} title="Vincular recepción" description="Selecciona de qué recepción proviene este material.">
      <form className="space-y-5" onSubmit={submit}>
        <Select label="Recepción de origen" value={selected} onChange={(changeEvent) => setSelected(changeEvent.target.value)} disabled={!candidates.length}>
          <option value="">Selecciona una recepción</option>
          {candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{receptionLabel(candidate)}</option>)}
        </Select>
        {!candidates.length && <Alert tone="warning" title="Sin recepciones compatibles">No existe una recepción compatible para vincular.</Alert>}
        {error && <Alert tone="danger" title="No pudimos vincular la recepción">{error}</Alert>}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button type="submit" loading={saving} disabled={!selected || saving}>Vincular recepción</Button></div>
      </form>
    </Modal>
  </>;
}
