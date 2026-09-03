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
    createJourney,
    listVehicleAssets,
} from "../api/transportApi";
import { selectableVehicleAssets } from "@/features/activos/utils/assetVehicleContract";

const initialForm = {
    vehicle: "",
    origin: "",
    destination: "",
    distance: "",
    load: "",
    fuel: "",
    source: "",
    loadState: "desconocido",
    tripType: "ida",
};

export default function TransportRecordModal({
    open,
    onClose,
    organizationId,
    workId,
    onCreated,
}) {
    const [form, setForm] = useState(initialForm);
    const [vehicles, setVehicles] = useState([]);
    const [sources, setSources] = useState([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!open) return;

        setForm(initialForm);
        setError("");

        listVehicleAssets(organizationId)
            .then((data) =>
                setVehicles(
                    Array.isArray(data)
                        ? data
                        : data?.results || [],
                ),
            );

        listDataSources(organizationId)
            .then((data) =>
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
                form.vehicle &&
                form.origin.trim() &&
                form.destination.trim() &&
                form.distance !== "" &&
                form.source,
            ),
        [form],
    );
    const vehicleOptions = useMemo(
        () => selectableVehicleAssets(vehicles),
        [vehicles],
    );

    async function submit(event) {
        event.preventDefault();

        if (!canSubmit) return;

        setSaving(true);
        setError("");

        try {
            const now = new Date().toISOString();

            const activity =
                await createOperationalActivity(
                    organizationId,
                    {
                        obra: workId,
                        tipo: "transporte",
                        nombre:
                            `Viaje ${form.origin} → ${form.destination}`,
                        timestamp_inicio: now,
                    },
                );

            await createJourney(
                organizationId,
                {
                    actividad: activity.id,
                    codigo:
                        `VIAJE-${Date.now()}`,
                    vehiculo:
                        Number(form.vehicle),
                    origen_nombre:
                        form.origin.trim(),
                    destino_nombre:
                        form.destination.trim(),
                    fecha_salida: now,
                    distancia:
                        form.distance,
                    carga:
                        form.load || null,
                    combustible:
                        form.fuel || null,
                    fuente:
                        Number(form.source),
                    estado_carga:
                        form.loadState,
                    tipo_trayecto:
                        form.tripType,
                    estado:
                        "completado",
                },
            );

            onClose();
            await onCreated?.();
        } catch (requestError) {
            setError(
                requestError.response?.data?.detail ||
                "No fue posible registrar el viaje.",
            );
        } finally {
            setSaving(false);
        }
    }

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Registrar viaje"
        >
            <form
                onSubmit={submit}
                className="space-y-4"
            >
                <Select
                    required
                    label="Vehículo"
                    value={form.vehicle}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            vehicle:
                                event.target.value,
                        }))
                    }
                >
                    <option value="">
                        Selecciona un vehículo
                    </option>

                    {vehicleOptions.map((item) => (
                        <option
                            key={item.id}
                            value={item.vehiculo.id}
                        >
                            {item.nombre}
                        </option>
                    ))}
                </Select>

                <Input
                    required
                    label="Origen"
                    value={form.origin}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            origin:
                                event.target.value,
                        }))
                    }
                />

                <Input
                    required
                    label="Destino"
                    value={form.destination}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            destination:
                                event.target.value,
                        }))
                    }
                />

                <Input
                    required
                    type="number"
                    step="any"
                    label="Distancia km"
                    value={form.distance}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            distance:
                                event.target.value,
                        }))
                    }
                />

                <Input
                    type="number"
                    step="any"
                    label="Carga t"
                    value={form.load}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            load:
                                event.target.value,
                        }))
                    }
                />

                <Input
                    type="number"
                    step="any"
                    label="Combustible L"
                    value={form.fuel}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            fuel:
                                event.target.value,
                        }))
                    }
                />

                <Select
                    label="Estado de carga"
                    value={form.loadState}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            loadState:
                                event.target.value,
                        }))
                    }
                >
                    <option value="desconocido">
                        Desconocido
                    </option>
                    <option value="cargado">
                        Cargado
                    </option>
                    <option value="parcialmente_cargado">
                        Parcialmente cargado
                    </option>
                    <option value="vacio">
                        Vacío
                    </option>
                </Select>

                <Select
                    label="Tipo de trayecto"
                    value={form.tripType}
                    onChange={(event) =>
                        setForm((current) => ({
                            ...current,
                            tripType:
                                event.target.value,
                        }))
                    }
                >
                    <option value="ida">
                        Ida
                    </option>
                    <option value="retorno">
                        Retorno
                    </option>
                    <option value="interno">
                        Interno
                    </option>
                    <option value="otro">
                        Otro
                    </option>
                </Select>

                <Select
                    required
                    label="Fuente del dato"
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
