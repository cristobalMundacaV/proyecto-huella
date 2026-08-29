import { UserRoundPlus } from "lucide-react";

import { Button, Input, Modal, Select } from "@/shared/ui";

export default function AssignDepartmentMemberModal({
    department,
    loading,
    onAssign,
    onClose,
    users,
}) {
    const formId = "assign-department-member-form";
    const available = users.filter((user) => user.activo !== false);

    function submit(event) {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const userId = Number(data.get("user_id"));
        if (!userId) return;
        onAssign({
            user_id: userId,
            cargo: String(data.get("cargo") || "").trim(),
        });
    }

    return (
        <Modal
            title="Agregar persona"
            description={`Asigna una persona del tenant a ${department.nombre}.`}
            icon={UserRoundPlus}
            onClose={loading ? undefined : onClose}
            size="sm"
            footer={(
                <div className="flex justify-end gap-3">
                    <Button variant="secondary" disabled={loading} onClick={onClose}>
                        Cancelar
                    </Button>
                    <Button
                        type="submit"
                        form={formId}
                        loading={loading}
                        disabled={!available.length}
                    >
                        Confirmar asignación
                    </Button>
                </div>
            )}
        >
            <form id={formId} className="space-y-5" onSubmit={submit}>
                {available.length ? (
                    <>
                        <Select
                            data-autofocus
                            name="user_id"
                            label="Persona"
                            defaultValue=""
                            required
                            disabled={loading}
                        >
                            <option value="" disabled>Selecciona una persona</option>
                            {available.map((user) => (
                                <option key={user.id} value={user.id}>
                                    {user.nombre} · {user.email || "Sin correo"}
                                </option>
                            ))}
                        </Select>
                        <Input
                            name="cargo"
                            label="Cargo en el departamento"
                            placeholder="Ej.: Encargada de información ambiental"
                            maxLength={140}
                            disabled={loading}
                        />
                    </>
                ) : (
                    <div role="status" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-center">
                        <UserRoundPlus className="mx-auto text-emerald-700" aria-hidden="true" />
                        <p className="mt-3 font-bold text-emerald-950">No hay personas disponibles</p>
                        <p className="mt-1 text-sm leading-5 text-emerald-800">
                            Todos los usuarios activos ya están asignados o aún no existen miembros en el tenant.
                        </p>
                    </div>
                )}
            </form>
        </Modal>
    );
}
