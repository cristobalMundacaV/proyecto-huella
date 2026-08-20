import {
    useState,
} from "react";

import {
    Link,
} from "react-router-dom";

import {
    Button,
    EmptyState,
    SectionHeader,
    StatusBadge,
    TableBody,
    TableCell,
    TableHead,
    TableShell,
} from "@/shared/ui";

import {
    formatDateTime,
    formatNumber,
} from "@/shared/utils/formatters";

import {
    isResourceReady,
    resourceData,
} from "../utils/operationSelectors";

import WorkSensorModal from "./WorkSensorModal";

export default function DomainSensorsPanel({
    domain,
    operation,
    organizationId,
    workId,
    onCreated,
}) {
    const [
        modalOpen,
        setModalOpen,
    ] = useState(false);

    const sensorsReady =
        isResourceReady(
            operation.sensors,
        );

    const points =
        resourceData(
            operation.points,
            [],
        );

    const sensors =
        resourceData(
            operation.sensors,
            [],
        ).filter(
            (sensor) =>
                sensor.ambito_operacional ===
                domain,
        );

    return (
        <section className="space-y-4">
            <SectionHeader
                eyebrow="IOT CONTEXTUAL"
                title="Sensores vinculados"
                description="Estado técnico, contexto y últimas lecturas de esta obra y ámbito."
                count={
                    sensors.length
                }
                action={
                    <Button
                        variant="secondary"
                        onClick={() =>
                            setModalOpen(
                                true,
                            )
                        }
                    >
                        Vincular sensor
                    </Button>
                }
            />

            {sensorsReady &&
                !sensors.length ? (
                <EmptyState
                    title="Sin sensores vinculados"
                    description="Este ámbito todavía no tiene sensores asociados a la obra."
                />
            ) : sensorsReady ? (
                <TableShell>
                    <TableHead>
                        <tr>
                            <TableCell as="th">
                                Sensor
                            </TableCell>
                            <TableCell as="th">
                                Contexto
                            </TableCell>
                            <TableCell as="th">
                                Estado
                            </TableCell>
                            <TableCell as="th">
                                Última comunicación
                            </TableCell>
                            <TableCell as="th">
                                Última lectura
                            </TableCell>
                            <TableCell as="th">
                                Calibración
                            </TableCell>
                        </tr>
                    </TableHead>

                    <TableBody
                        columns={6}
                    >
                        {sensors.map(
                            (sensor) => {
                                const reading =
                                    sensor
                                        .lecturas?.[0];

                                return (
                                    <tr
                                        key={
                                            sensor.id
                                        }
                                    >
                                        <TableCell>
                                            <Link
                                                className="font-bold text-[var(--brand-primary)]"
                                                to={`/operacion/sensores/${sensor.id}`}
                                            >
                                                {
                                                    sensor.nombre
                                                }
                                            </Link>

                                            <span className="block text-xs text-[var(--text-muted)]">
                                                {
                                                    sensor.dispositivo_id
                                                }
                                            </span>
                                        </TableCell>

                                        <TableCell>
                                            {sensor.punto_ambiental_nombre ||
                                                sensor.activo_nombre ||
                                                sensor.ubicacion ||
                                                "Obra"}
                                        </TableCell>

                                        <TableCell>
                                            <StatusBadge>
                                                {sensor.estado.replaceAll(
                                                    "_",
                                                    " ",
                                                )}
                                            </StatusBadge>
                                        </TableCell>

                                        <TableCell>
                                            {sensor.last_seen_at
                                                ? formatDateTime(
                                                    sensor.last_seen_at,
                                                )
                                                : "Sin comunicación"}
                                        </TableCell>

                                        <TableCell>
                                            {reading
                                                ? `${formatNumber(
                                                    reading.valor_numerico,
                                                )} ${reading.unidad}`
                                                : "Sin lecturas"}
                                        </TableCell>

                                        <TableCell>
                                            {sensor.proxima_calibracion ||
                                                sensor.ultima_calibracion ||
                                                "Sin calibración"}
                                        </TableCell>
                                    </tr>
                                );
                            },
                        )}
                    </TableBody>
                </TableShell>
            ) : (
                <EmptyState
                    title="Sensores no disponibles"
                    description="No fue posible cargar el contexto IoT."
                />
            )}

            <WorkSensorModal
                open={modalOpen}
                onClose={() =>
                    setModalOpen(
                        false,
                    )
                }
                organizationId={
                    organizationId
                }
                workId={workId}
                domain={domain}
                points={points}
                onCreated={
                    onCreated
                }
            />
        </section>
    );
}