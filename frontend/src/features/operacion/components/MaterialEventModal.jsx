import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    Button,
    Input,
    Modal,
    Select,
} from "@/shared/ui";

import {
    createOperationalActivity,
    listDataSources,
} from "../api/activityApi";

import {
    createMaterialEvent,
    listOperationalMaterials,
} from "../api/materialsApi";

const initialForm = {
    material: "",
    type: "recepcion",
    amount: "",
    unit: "",
    source: "",
};

export default function MaterialEventModal({
    open,
    onClose,
    organizationId,
    workId,
    onCreated,
}) {
    const [form, setForm] = useState(initialForm);
    const [materials, setMaterials] = useState([]);
    const [sources, setSources] = useState([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!open) return;

        setForm(initialForm);
        setError("");

        listOperationalMaterials(
            organizationId,
        ).then((data) =>
            setMaterials(
                Array.isArray(data)
                    ? data
                    : data?.results || [],
            ),
        );

        listDataSources(
            organizationId,
        ).then((data) =>
            setSources(
                Array.isArray(data)
                    ? data
                    : data?.results || [],
            ),
        );
    }, [open, organizationId]);

    const canSubmit = useMemo(
        () =>
            Boolean(
                form.material &&
                form.type &&
                form.amount !== "" &&
                form.unit.trim() &&
                form.source,
            ),
        [form],
    );

    async function submit(event) {
        event.preventDefault();

        if (!canSubmit) return;

        setSaving(true);
        setError("");

        try {
            const now =
                new Date().toISOString();

            const activity =
                await createOperationalActivity(
                    organizationId,
                    {
                        obra: workId,
                        tipo:
                            "movimiento_material",
                        nombre:
                            "Movimiento de material",
                        timestamp_inicio:
                            now,
                    },
                );

            await createMaterialEvent(
                organizationId,
                {
                    material:
                        Number(
                            form.material,
                        ),
                    actividad:
                        activity.id,
                    obra:
                        workId,
                    tipo:
                        form.type,
                    fecha_hora:
                        now,
                    cantidad:
                        form.amount,
                    unidad:
                        form.unit.trim(),
                    fuente:
                        Number(
                            form.source,
                        ),
                },
            );

            onClose();
            await onCreated?.();
        } catch (requestError) {
            setError(
                requestError.response?.data?.detail ||
                "No fue posible registrar el movimiento.",
            );
        } finally {
            setSaving(false);
        }
    }

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Registrar movimiento"
        >
            <form
                onSubmit={submit}
                className="space-y-4"
            >
                <Select
                    required
                    label="Material"
                    value={form.material}
                    onChange={(event) => {
                        const material =
                            materials.find(
                                (item) =>
                                    String(item.id) ===
                                    event.target.value,
                            );

                        setForm(
                            (current) => ({
                                ...current,
                                material:
                                    event.target.value,
                                unit:
                                    material?.unidad_base ||
                                    current.unit,
                            }),
                        );
                    }}
                >
                    <option value="">
                        Selecciona un material
                    </option>

                    {materials.map((item) => (
                        <option
                            key={item.id}
                            value={item.id}
                        >
                            {item.nombre}
                        </option>
                    ))}
                </Select>

                <Select
                    required
                    label="Movimiento"
                    value={form.type}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            type:
                                event.target.value,
                        }))
                    }
                >
                    <option value="adquisicion">
                        Adquisición
                    </option>
                    <option value="recepcion">
                        Recepción
                    </option>
                    <option value="uso">
                        Uso
                    </option>
                    <option value="sobrante">
                        Sobrante
                    </option>
                    <option value="reutilizacion">
                        Reutilización
                    </option>
                    <option value="devolucion">
                        Devolución
                    </option>
                    <option value="residuo">
                        Residuo
                    </option>
                    <option value="despacho">
                        Despacho
                    </option>
                </Select>

                <Select
                    required
                    label="Unidad de medida"
                    value={form.unit}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            unit:
                                event.target.value,
                        }))
                    }
                >
                    {form.unit ? (
                        <option value={form.unit}>{form.unit}</option>
                    ) : (
                        <option value="">Selecciona primero un material</option>
                    )}
                </Select>

                <Input
                    required
                    type="number"
                    step="any"
                    label="Cantidad"
                    suffix={form.unit}
                    value={form.amount}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            amount:
                                event.target.value,
                        }))
                    }
                />

                <Select
                    required
                    label="Fuente"
                    value={form.source}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            source:
                                event.target.value,
                        }))
                    }
                >
                    <option value="">
                        Selecciona una fuente
                    </option>

                    {sources.map((source) => (
                        <option
                            key={source.id}
                            value={source.id}
                        >
                            {source.nombre}
                        </option>
                    ))}
                </Select>

                {error && (
                    <p>{error}</p>
                )}

                <div className="flex justify-end gap-2">
                    <Button
                        type="button"
                        onClick={onClose}
                    >
                        Cancelar
                    </Button>

                    <Button
                        type="submit"
                        disabled={
                            !canSubmit ||
                            saving
                        }
                    >
                        Registrar
                    </Button>
                </div>
            </form>
        </Modal>
    );
}
