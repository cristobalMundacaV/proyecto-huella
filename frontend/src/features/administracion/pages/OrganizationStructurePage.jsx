import { useCallback, useEffect, useState } from "react";
import { Building2, Loader2, Plus, Trash2, UserRoundMinus, UsersRound } from "lucide-react";

import Toast from "@/shared/components/Toast";
import { Button, EmptyState, ErrorState, Modal } from "@/shared/ui";
import { humanizeApiError } from "@/shared/utils/apiErrors";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
    addDepartmentUser,
    createDepartment,
    deleteDepartment,
    getDepartmentUsers,
    getDepartments,
    getOrganizationUsers,
    removeDepartmentUser,
    updateDepartmentUser,
} from "../api/organizationStructureApi";
import AssignDepartmentMemberModal from "../components/AssignDepartmentMemberModal";
import CreateDepartmentModal from "../components/CreateDepartmentModal";
import DepartmentCard from "../components/DepartmentCard";

export default function OrganizationStructurePage() {
    const { activeOrganizacionId } = useOrganizacionActiva();
    const [departments, setDepartments] = useState([]);
    const [tenantUsers, setTenantUsers] = useState([]);
    const [usersByDepartment, setUsersByDepartment] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [modal, setModal] = useState(null);
    const [confirmation, setConfirmation] = useState(null);
    const [busy, setBusy] = useState(false);
    const [toast, setToast] = useState(null);

    const load = useCallback(async () => {
        if (!activeOrganizacionId) {
            setDepartments([]);
            setTenantUsers([]);
            setUsersByDepartment({});
            setLoading(false);
            return;
        }
        setLoading(true);
        setError("");
        try {
            const [departmentRows, organizationUsers] = await Promise.all([
                getDepartments(activeOrganizacionId),
                getOrganizationUsers(activeOrganizacionId),
            ]);
            const active = departmentRows.filter((department) => department.activa);
            const assignments = await Promise.all(
                active.map(async (department) => [
                    department.id,
                    await getDepartmentUsers(activeOrganizacionId, department.id),
                ]),
            );
            setDepartments(active);
            setTenantUsers(organizationUsers);
            setUsersByDepartment(Object.fromEntries(assignments));
        } catch (requestError) {
            setError(humanizeApiError(requestError, "No fue posible cargar la estructura organizacional."));
        } finally {
            setLoading(false);
        }
    }, [activeOrganizacionId]);

    useEffect(() => {
        load();
    }, [load]);

    async function mutate(action, success) {
        setBusy(true);
        try {
            await action();
            await load();
            setModal(null);
            setConfirmation(null);
            setToast({ id: Date.now(), message: success.title, subtitle: success.subtitle });
        } catch (requestError) {
            setToast({
                id: Date.now(),
                tone: "error",
                message: "No pudimos completar la acción",
                subtitle: humanizeApiError(requestError),
            });
        } finally {
            setBusy(false);
        }
    }

    function handleCreate(payload) {
        return mutate(
            () => createDepartment(activeOrganizacionId, payload),
            { title: "Departamento creado", subtitle: `${payload.nombre} ya forma parte de la estructura.` },
        );
    }

    function handleAssign(payload) {
        const department = modal.department;
        return mutate(
            () => addDepartmentUser(activeOrganizacionId, department.id, payload),
            { title: "Persona asignada", subtitle: `La asignación a ${department.nombre} quedó guardada.` },
        );
    }

    function handleSetPrimary(department, user, isPrimary) {
        return mutate(
            () => updateDepartmentUser(
                activeOrganizacionId,
                department.id,
                user.id,
                { es_principal: isPrimary },
            ),
            {
                title: isPrimary ? "Área principal actualizada" : "Área principal desmarcada",
                subtitle: isPrimary
                    ? `${department.nombre} ahora es el área principal de ${user.nombre}.`
                    : `${department.nombre} dejó de ser el área principal de ${user.nombre}.`,
            },
        );
    }

    function confirmAction() {
        if (confirmation.kind === "department") {
            return mutate(
                () => deleteDepartment(activeOrganizacionId, confirmation.department.id),
                {
                    title: "Departamento eliminado",
                    subtitle: confirmation.users.length
                        ? "El área se desactivó para conservar su historial y asignaciones."
                        : "El departamento fue retirado de la estructura activa.",
                },
            );
        }
        return mutate(
            () => removeDepartmentUser(
                activeOrganizacionId,
                confirmation.department.id,
                confirmation.user.id,
            ),
            {
                title: "Asignación eliminada",
                subtitle: `${confirmation.user.nombre} ya no pertenece a ${confirmation.department.nombre}.`,
            },
        );
    }

    const assignedIds = modal?.kind === "assign"
        ? new Set((usersByDepartment[modal.department.id] || []).map((user) => user.user_id))
        : new Set();
    const availableUsers = tenantUsers.filter((user) => !assignedIds.has(user.id));

    if (error) {
        return <ErrorState title="No pudimos cargar la estructura" description={error} onRetry={load} />;
    }

    return (
        <section className="space-y-6">
            <Toast {...toast} toastKey={toast?.id} onClose={() => setToast(null)} />

            <header className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="mb-2 flex items-center gap-2 text-emerald-700">
                        <UsersRound aria-hidden="true" size={20} />
                        <span className="text-xs font-bold uppercase tracking-wider">Organización</span>
                    </div>
                    <h1 className="text-2xl font-black tracking-tight text-slate-950">Estructura organizacional</h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                        Configura los departamentos y las personas que participan en la operación de la organización.
                    </p>
                </div>
                <Button
                    type="button"
                    leftIcon={Plus}
                    disabled={loading || busy}
                    onClick={() => setModal({ kind: "create" })}
                    className="min-h-11 rounded-xl shadow-sm"
                >
                    Crear departamento
                </Button>
            </header>

            {loading ? (
                <div role="status" className="flex min-h-64 items-center justify-center rounded-3xl border border-slate-200 bg-white text-sm font-bold text-slate-600 shadow-sm">
                    <Loader2 className="mr-2 animate-spin text-emerald-700" aria-hidden="true" />
                    Cargando estructura organizacional
                </div>
            ) : departments.length ? (
                <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                    {departments.map((department) => (
                        <DepartmentCard
                            key={department.id}
                            busy={busy}
                            department={department}
                            users={usersByDepartment[department.id] || []}
                            onAddUser={(selected) => setModal({ kind: "assign", department: selected })}
                            onDelete={(selected) => setConfirmation({
                                kind: "department",
                                department: selected,
                                users: usersByDepartment[selected.id] || [],
                            })}
                            onSetPrimary={handleSetPrimary}
                            onRemoveUser={(selected, user) => setConfirmation({
                                kind: "user",
                                department: selected,
                                user,
                            })}
                        />
                    ))}
                </div>
            ) : (
                <EmptyState
                    icon={Building2}
                    title="Tu estructura está lista para configurarse"
                    description="Crea el primer departamento para organizar las áreas que generan y administran información."
                    primaryAction={<Button leftIcon={Plus} onClick={() => setModal({ kind: "create" })}>Crear departamento</Button>}
                />
            )}

            {modal?.kind === "create" && (
                <CreateDepartmentModal loading={busy} onClose={() => setModal(null)} onCreate={handleCreate} />
            )}
            {modal?.kind === "assign" && (
                <AssignDepartmentMemberModal
                    department={modal.department}
                    loading={busy}
                    users={availableUsers}
                    onClose={() => setModal(null)}
                    onAssign={handleAssign}
                />
            )}
            {confirmation && (
                <Modal
                    title={confirmation.kind === "department" ? "Eliminar departamento" : "Quitar persona"}
                    description={confirmation.kind === "department"
                        ? `Confirma qué ocurrirá con ${confirmation.department.nombre}.`
                        : `Confirma la asignación que deseas retirar de ${confirmation.department.nombre}.`}
                    icon={confirmation.kind === "department" ? Trash2 : UserRoundMinus}
                    onClose={busy ? undefined : () => setConfirmation(null)}
                    size="sm"
                    footer={(
                        <div className="flex justify-end gap-3">
                            <Button variant="secondary" disabled={busy} onClick={() => setConfirmation(null)}>Cancelar</Button>
                            <Button variant="danger" loading={busy} onClick={confirmAction}>
                                {confirmation.kind === "department" ? "Eliminar departamento" : "Quitar persona"}
                            </Button>
                        </div>
                    )}
                >
                    <div className="rounded-2xl border border-red-100 bg-red-50/70 p-5 text-sm leading-6 text-slate-700">
                        {confirmation.kind === "department" && confirmation.users.length
                            ? `Este departamento tiene ${confirmation.users.length} persona${confirmation.users.length === 1 ? "" : "s"} asignada${confirmation.users.length === 1 ? "" : "s"}. Se desactivará para conservar el historial existente.`
                            : confirmation.kind === "department"
                                ? "El departamento se retirará de la estructura activa. Esta acción requiere confirmación."
                                : `${confirmation.user.nombre} dejará de aparecer en este departamento. Su cuenta y acceso al tenant no serán eliminados.`}
                    </div>
                </Modal>
            )}
        </section>
    );
}
