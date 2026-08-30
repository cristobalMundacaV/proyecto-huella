import { useState } from "react";
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
    const [isPrimary, setIsPrimary] = useState(false);

    function submit(event) {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const userId = Number(data.get("user_id"));
        if (!userId) return;
        onAssign({
            user_id: userId,
            cargo: String(data.get("cargo") || "").trim(),
            es_principal: isPrimary,
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
                        <label className="group flex w-full cursor-pointer items-start gap-3.5 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 transition hover:border-emerald-300 hover:bg-emerald-50 focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/25">
                            <input
                                type="checkbox"
                                name="es_principal"
                                checked={isPrimary}
                                disabled={loading}
                                onChange={(event) => setIsPrimary(event.target.checked)}
                                className="mt-0.5 h-5 w-5 shrink-0 cursor-pointer rounded border-emerald-300 text-emerald-700 accent-emerald-700 focus:ring-emerald-500 disabled:cursor-not-allowed"
                            />
                            <span className="min-w-0">
                                <span className="block text-sm font-bold leading-5 text-emerald-950">
                                    Definir como área principal
                                </span>
                                <span className="mt-1 block text-xs leading-5 text-emerald-900/80">
                                    Marca esta opción si este departamento será el área principal de la persona dentro de la organización. Solo una asignación puede ser principal al mismo tiempo.
                                </span>
                            </span>
                        </label>
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
