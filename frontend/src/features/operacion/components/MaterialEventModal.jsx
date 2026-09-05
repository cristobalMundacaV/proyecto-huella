import { useEffect, useMemo, useState } from "react";
import { Boxes, PackagePlus } from "lucide-react";
import Toast from "@/shared/components/Toast";
import { Alert, Button, Input, Modal, Select, Textarea } from "@/shared/ui";
import { humanizeApiError } from "@/shared/utils/apiErrors";
import { createOperationalActivity, listDataSources } from "../api/activityApi";
import { createMaterialEvent, createOperationalMaterial, listOperationalMaterials } from "../api/materialsApi";
import { listEvidenceTypes } from "../api/sectorFlowsApi";
import { MATERIAL_OPERATIONAL_CATEGORIES, MATERIAL_OPERATIONAL_UNITS, compatibleMaterialReceptions, createMaterialMovementTechnicalCode, materialActivityPayload, materialEventPayload, operationalMaterialPayload } from "../utils/materialRecordContract";

const initialForm = { material: "", type: "recepcion", amount: "", unit: "", source: "", originReception: "", evidenceFile: null, evidenceType: "", evidenceName: "" };
const initialMaterial = { name: "", category: "cemento", baseUnit: "kg", supplier: "", description: "" };
const Section = ({ title, children }) => <section className="space-y-4 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface-subtle)] p-4"><h3 className="font-black text-[var(--text-primary)]">{title}</h3><div className="grid gap-4 sm:grid-cols-2">{children}</div></section>;

function MaterialCreateModal({ open, onClose, organizationId, onCreated, onError }) {
    const [form, setForm] = useState(initialMaterial);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    useEffect(() => { if (open) { setForm(initialMaterial); setError(""); } }, [open]);
    const setField = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
    const canSubmit = Boolean(form.name.trim() && form.category && form.baseUnit);
    async function submit(event) {
        event.preventDefault();
        if (!canSubmit) return;
        setSaving(true); setError("");
        try {
            const created = await createOperationalMaterial(organizationId, operationalMaterialPayload(form));
            await onCreated(created); onClose();
        } catch (requestError) {
            const message = humanizeApiError(requestError, "No fue posible crear el material. Revisa los datos e inténtalo nuevamente.");
            setError(message); onError(message);
        } finally { setSaving(false); }
    }
    return <Modal open={open} onClose={onClose} eyebrow="CATÁLOGO OPERACIONAL" icon={PackagePlus} title="Crear nuevo material" description="Define el material una vez para reutilizarlo en los movimientos de la organización.">
        <form onSubmit={submit} className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
                <Input required label="Nombre" value={form.name} onChange={setField("name")} />
                <Select required label={"Categor\u00eda"} value={form.category} onChange={setField("category")}>{MATERIAL_OPERATIONAL_CATEGORIES.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}</Select>
                <Select required label="Unidad de medida" value={form.baseUnit} onChange={setField("baseUnit")}>{MATERIAL_OPERATIONAL_UNITS.map((unit) => <option key={unit.value} value={unit.value}>{unit.label}</option>)}</Select>
                <Input label="Proveedor / fabricante" value={form.supplier} onChange={setField("supplier")} />
                <Textarea label="Descripción" value={form.description} onChange={setField("description")} />
            </div>
            {error && <Alert tone="danger" title="No pudimos crear el material">{error}</Alert>}
            <div className="flex justify-end gap-2"><Button type="button" variant="secondary" disabled={saving} onClick={onClose}>Volver</Button><Button type="submit" loading={saving} disabled={!canSubmit || saving}>Crear material</Button></div>
        </form>
    </Modal>;
}

export default function MaterialEventModal({ open, onClose, organizationId, workId, events = [], onCreated }) {
    const [form, setForm] = useState(initialForm);
    const [materials, setMaterials] = useState([]);
    const [sources, setSources] = useState([]);
    const [evidenceTypes, setEvidenceTypes] = useState([]);
    const [addingEvidence, setAddingEvidence] = useState(false);
    const [creatingMaterial, setCreatingMaterial] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [toast, setToast] = useState(null);
    useEffect(() => {
        if (!open) return;
        setForm(initialForm); setAddingEvidence(false); setError("");
        listOperationalMaterials(organizationId).then((data) => setMaterials(Array.isArray(data) ? data : data?.results || []));
        listDataSources(organizationId, "materiales").then((data) => setSources(Array.isArray(data) ? data : data?.results || []));
        listEvidenceTypes("materiales").then((data) => setEvidenceTypes(Array.isArray(data) ? data : []));
    }, [open, organizationId]);
    const selectedMaterial = useMemo(() => materials.find((item) => String(item.id) === form.material), [materials, form.material]);
    const isUsage = ["uso", "consumo"].includes(form.type);
    const compatibleReceptions = useMemo(() => compatibleMaterialReceptions(events, { materialId: form.material, workId, unit: form.unit, timestamp: new Date().toISOString() }), [events, form.material, form.unit, workId]);
    useEffect(() => {
        if (!isUsage) return setForm((current) => current.originReception ? { ...current, originReception: "" } : current);
        setForm((current) => {
            if (compatibleReceptions.some((item) => String(item.id) === current.originReception)) return current;
            return { ...current, originReception: compatibleReceptions.length === 1 ? String(compatibleReceptions[0].id) : "" };
        });
    }, [isUsage, compatibleReceptions]);
    const canSubmit = Boolean(form.material && form.type && form.amount !== "" && form.unit && form.source && (!addingEvidence || (form.evidenceFile && form.evidenceType)));
    const setField = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
    async function materialCreated(created) {
        const refreshed = await listOperationalMaterials(organizationId);
        setMaterials(Array.isArray(refreshed) ? refreshed : refreshed?.results || []);
        setForm((current) => ({ ...current, material: String(created.id), unit: created.unidad_base }));
        setToast({ id: Date.now(), tone: "success", message: "Material creado", subtitle: `${created.nombre} quedó seleccionado para este movimiento.` });
    }
    async function submit(event) {
        event.preventDefault();
        if (!canSubmit) return;
        setSaving(true); setError("");
        const timestamp = new Date().toISOString();
        const code = createMaterialMovementTechnicalCode();
        try {
            const activity = await createOperationalActivity(organizationId, materialActivityPayload({ workId, form, material: selectedMaterial, timestamp, code }));
            await createMaterialEvent(organizationId, materialEventPayload({ activityId: activity.id, workId, form, timestamp }));
            setToast({ id: Date.now(), tone: "success", message: "Movimiento registrado", subtitle: "El movimiento y su fuente quedaron asociados a la obra." });
            onClose(); await onCreated?.();
        } catch (requestError) {
            const message = humanizeApiError(requestError, "No fue posible registrar el movimiento. Revisa los datos e inténtalo nuevamente.");
            setError(message); setToast({ id: Date.now(), tone: "error", message: "No pudimos registrar el movimiento", subtitle: message });
        } finally { setSaving(false); }
    }
    return <>
        <Toast {...toast} toastKey={toast?.id} onClose={() => setToast(null)} />
        <Modal open={open} onClose={onClose} eyebrow="REGISTRO OPERACIONAL" icon={Boxes} title="Registrar movimiento de material" description="El movimiento quedará asociado a esta obra y conservará su fuente y trazabilidad.">
            <form onSubmit={submit} className="space-y-5">
                <Section title="Material"><div><Select required label="Material" value={form.material} onChange={(event) => { const material = materials.find((item) => String(item.id) === event.target.value); setForm((current) => ({ ...current, material: event.target.value, unit: material?.unidad_base || "" })); }}><option value="">Selecciona un material</option>{materials.filter((item) => item.activo).map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</Select><Button type="button" variant="ghost" className="mt-2" onClick={() => setCreatingMaterial(true)}>+ Crear nuevo material</Button></div></Section>
                <Section title="Movimiento">
                    <Select required label="Tipo de movimiento" value={form.type} onChange={setField("type")}><option value="adquisicion">Adquisición</option><option value="recepcion">Recepción</option><option value="uso">Uso</option><option value="consumo">Consumo</option><option value="sobrante">Sobrante</option><option value="reutilizacion">Reutilización</option><option value="devolucion">Devolución</option><option value="residuo">Residuo</option><option value="despacho">Despacho</option></Select>
                    <Input required type="number" step="any" label="Cantidad" suffix={form.unit} value={form.amount} onChange={setField("amount")} />
                    <Select required label="Unidad" value={form.unit} onChange={setField("unit")} disabled={!selectedMaterial}><option value="">Selecciona primero un material</option>{selectedMaterial?.unidad_base && <option value={selectedMaterial.unidad_base}>{selectedMaterial.unidad_base}</option>}</Select>
                    {isUsage && <div className="sm:col-span-2"><Select label="Recepción de origen" value={form.originReception} onChange={setField("originReception")}><option value="">Selecciona una recepción</option>{compatibleReceptions.map((reception) => <option key={reception.id} value={reception.id}>{new Date(reception.fecha_hora).toLocaleDateString("es-CL")} · Recepción {reception.cantidad_detalle?.valor_numerico} {reception.cantidad_detalle?.unidad} · {reception.cantidad_detalle?.fuente_detalle?.nombre || "Fuente no informada"}</option>)}</Select>{compatibleReceptions.length === 0 && <Alert tone="warning" title="Trazabilidad pendiente">No existe una recepción compatible para vincular. El movimiento podrá guardarse, pero quedará pendiente de trazabilidad.</Alert>}</div>}
                </Section>
                <Section title="Trazabilidad">
                    <Select required label="Fuente del dato" value={form.source} onChange={setField("source")}><option value="">Selecciona una fuente</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.nombre}</option>)}</Select>
                    {!addingEvidence && <div className="sm:col-span-2"><Button type="button" variant="ghost" onClick={() => setAddingEvidence(true)}>+ Agregar respaldo</Button></div>}
                    {addingEvidence && <>
                        <Input required type="file" label="Archivo" onChange={(event) => setForm((current) => ({ ...current, evidenceFile: event.target.files?.[0] || null }))} />
                        <Select required label="Tipo de respaldo" value={form.evidenceType} onChange={setField("evidenceType")}><option value="">Selecciona un tipo</option>{evidenceTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</Select>
                        <Input label="Nombre del documento" value={form.evidenceName} onChange={setField("evidenceName")} />
                        <div className="flex items-end"><Button type="button" variant="ghost" onClick={() => { setAddingEvidence(false); setForm((current) => ({ ...current, evidenceFile: null, evidenceType: "", evidenceName: "" })); }}>Quitar respaldo</Button></div>
                        {form.evidenceFile && <p className="sm:col-span-2 text-sm text-[var(--text-muted)]">Archivo seleccionado: <strong>{form.evidenceFile.name}</strong></p>}
                    </>}
                </Section>
                {error && <Alert tone="danger" title="No pudimos registrar el movimiento">{error}</Alert>}
                <div className="flex justify-end gap-2"><Button type="button" variant="secondary" disabled={saving} onClick={onClose}>Cancelar</Button><Button type="submit" loading={saving} disabled={!canSubmit || saving}>Registrar movimiento</Button></div>
            </form>
        </Modal>
        <MaterialCreateModal open={creatingMaterial} onClose={() => setCreatingMaterial(false)} organizationId={organizationId} onCreated={materialCreated} onError={(message) => setToast({ id: Date.now(), tone: "error", message: "No pudimos crear el material", subtitle: message })} />
    </>;
}
