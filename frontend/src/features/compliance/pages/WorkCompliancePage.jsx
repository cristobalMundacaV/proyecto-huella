import {
    useEffect,
    useState,
} from "react";

import {
    AlertTriangle,
    CheckCircle2,
    FileText,
    ShieldCheck,
} from "lucide-react";

import {
    useOutletContext,
} from "react-router-dom";

import {
    useOrganizacionActiva,
} from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
    EmptyState,
    KpiCard,
    SectionHeader,
    StatusBadge,
    TableBody,
    TableCell,
    TableHead,
    TableShell,
} from "@/shared/ui";

import {
    getComplianceAlerts,
    getComplianceDocuments,
    getComplianceSummary,
} from "../api/complianceApi";


export default function WorkCompliancePage() {
    const workspace =
        useOutletContext() || {};

    const {
        activeOrganizacionId,
    } = useOrganizacionActiva();

    const workId =
        workspace.obra?.id ||
        workspace.obra?.obra_id;

    const [
        state,
        setState,
    ] = useState({
        loading: true,
        summary: null,
        documents: [],
        alerts: [],
    });


    useEffect(
        () => {
            if (
                !activeOrganizacionId ||
                !workId
            ) {
                return;
            }

            const params = {
                obra: workId,
            };

            Promise.all([
                getComplianceSummary(
                    activeOrganizacionId,
                    params,
                ),

                getComplianceDocuments(
                    activeOrganizacionId,
                    params,
                ),

                getComplianceAlerts(
                    activeOrganizacionId,
                    params,
                ),
            ]).then(
                ([
                    summary,
                    documents,
                    alerts,
                ]) => {
                    setState({
                        loading: false,
                        summary,
                        documents,
                        alerts,
                    });
                },
            );
        },
        [
            activeOrganizacionId,
            workId,
        ],
    );


    if (
        state.loading
    ) {
        return (
            <p className="text-sm text-[var(--text-muted)]">
                Cargando cumplimiento...
            </p>
        );
    }


    return (
        <main className="space-y-6">
            <SectionHeader
                eyebrow="CUMPLIMIENTO"
                title="Cumplimiento ambiental"
                description="Documentos y alertas correspondientes exclusivamente a esta obra."
            />

            <div className="grid gap-4 md:grid-cols-4">
                <KpiCard
                    label="Documentos"
                    value={
                        state.summary
                            ?.total_documentos || 0
                    }
                    icon={FileText}
                />

                <KpiCard
                    label="Validados"
                    value={
                        state.summary
                            ?.documentos_validados || 0
                    }
                    icon={CheckCircle2}
                />

                <KpiCard
                    label="Alertas abiertas"
                    value={
                        state.summary
                            ?.alertas_abiertas || 0
                    }
                    icon={AlertTriangle}
                />

                <KpiCard
                    label="Cumplimiento"
                    value={
                        state.summary
                            ?.compliance_pct ?? 0
                    }
                    unit="%"
                    icon={ShieldCheck}
                />
            </div>

            <section className="space-y-3">
                <SectionHeader
                    eyebrow="ANTECEDENTES"
                    title="Documentos ambientales"
                />

                {!state.documents.length ? (
                    <EmptyState
                        icon={FileText}
                        title="Sin documentos asociados"
                        description="Todavía no existen documentos ambientales vinculados a esta obra."
                    />
                ) : (
                    <TableShell>
                        <TableHead>
                            <tr>
                                <TableCell as="th">
                                    Documento
                                </TableCell>

                                <TableCell as="th">
                                    Tipo
                                </TableCell>

                                <TableCell as="th">
                                    Estado
                                </TableCell>

                                <TableCell as="th">
                                    Fecha
                                </TableCell>
                            </tr>
                        </TableHead>

                        <TableBody
                            columns={4}
                        >
                            {state.documents.map(
                                (item) => (
                                    <tr
                                        key={item.id}
                                    >
                                        <TableCell>
                                            <b>
                                                {item.nombre ||
                                                    item.nombre_archivo ||
                                                    `Documento ${item.id}`}
                                            </b>
                                        </TableCell>

                                        <TableCell>
                                            {item.tipo_documento ||
                                                item.tipo ||
                                                "—"}
                                        </TableCell>

                                        <TableCell>
                                            <StatusBadge>
                                                {String(
                                                    item.estado_validacion ||
                                                    item.estado ||
                                                    "pendiente"
                                                ).replaceAll(
                                                    "_",
                                                    " ",
                                                )}
                                            </StatusBadge>
                                        </TableCell>

                                        <TableCell>
                                            {item.fecha_documento ||
                                                item.created_at ||
                                                "—"}
                                        </TableCell>
                                    </tr>
                                ),
                            )}
                        </TableBody>
                    </TableShell>
                )}
            </section>

            <section className="space-y-3">
                <SectionHeader
                    eyebrow="ALERTAS"
                    title="Alertas de cumplimiento"
                />

                {!state.alerts.length ? (
                    <EmptyState
                        icon={CheckCircle2}
                        title="Sin alertas abiertas"
                        description="No existen alertas de cumplimiento asociadas a esta obra."
                    />
                ) : (
                    <TableShell>
                        <TableHead>
                            <tr>
                                <TableCell as="th">
                                    Alerta
                                </TableCell>

                                <TableCell as="th">
                                    Severidad
                                </TableCell>

                                <TableCell as="th">
                                    Estado
                                </TableCell>
                            </tr>
                        </TableHead>

                        <TableBody
                            columns={3}
                        >
                            {state.alerts.map(
                                (item) => (
                                    <tr
                                        key={item.id}
                                    >
                                        <TableCell>
                                            {item.mensaje ||
                                                item.descripcion ||
                                                `Alerta ${item.id}`}
                                        </TableCell>

                                        <TableCell>
                                            <StatusBadge
                                                tone={
                                                    item.severidad ===
                                                        "rojo"
                                                        ? "danger"
                                                        : "warning"
                                                }
                                            >
                                                {item.severidad}
                                            </StatusBadge>
                                        </TableCell>

                                        <TableCell>
                                            {String(
                                                item.estado
                                            ).replaceAll(
                                                "_",
                                                " ",
                                            )}
                                        </TableCell>
                                    </tr>
                                ),
                            )}
                        </TableBody>
                    </TableShell>
                )}
            </section>
        </main>
    );
}