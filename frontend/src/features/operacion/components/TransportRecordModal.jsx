import { useEffect, useMemo, useState } from "react";
import { Truck } from "lucide-react";

import { selectableVehicleAssets } from "@/features/activos/utils/assetVehicleContract";
import Toast from "@/shared/components/Toast";
import { Alert, Button, Input, Modal, Select } from "@/shared/ui";
import { humanizeApiError } from "@/shared/utils/apiErrors";

import { createOperationalActivity, listDataSources } from "../api/activityApi";
import { createJourney, listVehicleAssets } from "../api/transportApi";
import {
    createJourneyTechnicalCode,
    transportActivityPayload,
    transportJourneyPayload,
} from "../utils/transportRecordContract";

const initialForm = {
    vehicle: "", origin: "", destination: "", distance: "", load: "", fuel: "",
    source: "", loadState: "desconocido", tripType: "ida",
};

const Section = ({ title, children }) => (
    <section className="space-y-4 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface-subtle)] p-4">
        <h3 className="font-black text-[var(--text-primary)]">{title}</h3>
        <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </section>
);

export default function TransportRecordModal({ open, onClose, organizationId, workId, onCreated }) {
    const [form, setForm] = useState(initialForm);
    const [vehicles, setVehicles] = useState([]);
    const [sources, setSources] = useState([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [toast, setToast] = useState(null);

    useEffect(() => {
        if (!open) return;
        setForm(initialForm);
        setError("");
        listVehicleAssets(organizationId).then((data) =>
            setVehicles(Array.isArray(data) ? data : data?.results || []),
        );
        listDataSources(organizationId, "transporte").then((data) =>
            setSources(Array.isArray(data) ? data : data?.results || []),
        );
    }, [open, organizationId]);

    const canSubmit = useMemo(
        () => Boolean(form.vehicle && form.origin.trim() && form.destination.trim()
            && form.distance !== "" && form.source),
        [form],
    );
    const vehicleOptions = useMemo(() => selectableVehicleAssets(vehicles), [vehicles]);
    const setField = (field) => (event) =>
        setForm((current) => ({ ...current, [field]: event.target.value }));

    async function submit(event) {
        event.preventDefault();
        if (!canSubmit) return;
        setSaving(true);
        setError("");
        const timestamp = new Date().toISOString();
        const code = createJourneyTechnicalCode();

        try {
            const activity = await createOperationalActivity(
                organizationId,
                transportActivityPayload({ workId, form, timestamp, code }),
            );
            await createJourney(
                organizationId,
                transportJourneyPayload({ activityId: activity.id, form, timestamp, code }),
            );
            setToast({
                id: Date.now(), tone: "success", message: "Viaje registrado",
                subtitle: "El viaje y sus magnitudes quedaron asociados a la obra.",
            });
            onClose();
            await onCreated?.();
        } catch (requestError) {
            const message = humanizeApiError(
                requestError,
                "No fue posible registrar el viaje. Revisa los datos e inténtalo nuevamente.",
            );
            setError(message);
            setToast({
                id: Date.now(), tone: "error", message: "No pudimos registrar el viaje",
                subtitle: message,
            });
        } finally {
            setSaving(false);
        }
    }

    return <>
        <Toast {...toast} toastKey={toast?.id} onClose={() => setToast(null)} />
        <Modal
            open={open}
            onClose={onClose}
            eyebrow="REGISTRO OPERACIONAL"
            icon={Truck}
            title="Registrar viaje"
            description="Asocia el viaje a esta obra y conserva la fuente de sus magnitudes operacionales."
        >
            <form onSubmit={submit} className="space-y-5">
                <Section title="Trayecto">
                    <Select required label="Vehículo" value={form.vehicle} onChange={setField("vehicle")}>
                        <option value="">Selecciona un vehículo</option>
                        {vehicleOptions.map((item) => (
                            <option key={item.id} value={item.vehiculo.id}>{item.nombre}</option>
                        ))}
                    </Select>
                    <Input required label="Origen" value={form.origin} onChange={setField("origin")} />
                    <Input required label="Destino" value={form.destination} onChange={setField("destination")} />
                </Section>

                <Section title="Magnitudes">
                    <Input required type="number" step="any" label="Distancia" suffix="km" value={form.distance} onChange={setField("distance")} />
                    <Input type="number" step="any" label="Carga" suffix="t" value={form.load} onChange={setField("load")} />
                    <Input type="number" step="any" label="Combustible" suffix="L" value={form.fuel} onChange={setField("fuel")} />
                </Section>

                <Section title="Contexto">
                    <Select label="Estado de carga" value={form.loadState} onChange={setField("loadState")}>
                        <option value="desconocido">Desconocido</option>
                        <option value="cargado">Cargado</option>
                        <option value="parcialmente_cargado">Parcialmente cargado</option>
                        <option value="vacio">Vacío</option>
                    </Select>
                    <Select label="Tipo de trayecto" value={form.tripType} onChange={setField("tripType")}>
                        <option value="ida">Ida</option>
                        <option value="retorno">Retorno</option>
                        <option value="interno">Interno</option>
                        <option value="otro">Otro</option>
                    </Select>
                </Section>

                <Section title="Trazabilidad">
                    <Select required label="Fuente del dato" value={form.source} onChange={setField("source")}>
                        <option value="">Selecciona una fuente</option>
                        {sources.map((source) => (
                            <option key={source.id} value={source.id}>{source.nombre}</option>
                        ))}
                    </Select>
                </Section>

                {error && <Alert tone="danger" title="No pudimos registrar el viaje">{error}</Alert>}
                <div className="flex justify-end gap-2">
                    <Button type="button" variant="secondary" disabled={saving} onClick={onClose}>Cancelar</Button>
                    <Button type="submit" loading={saving} disabled={!canSubmit || saving}>Registrar viaje</Button>
                </div>
            </form>
        </Modal>
    </>;
}
