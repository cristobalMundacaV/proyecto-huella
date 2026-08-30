import {
    Plus,
    Trash2,
    UserRound,
    UserRoundPlus,
    UsersRound,
    X,
} from "lucide-react";

import { Button, IconButton } from "@/shared/ui";

import { DEPARTMENT_PRESENTATION } from "../config/departmentPresentation";

export default function DepartmentCard({
    busy,
    department,
    onAddUser,
    onDelete,
    onRemoveUser,
    users = [],
}) {
    const presentation = DEPARTMENT_PRESENTATION[department.tipo]
        || DEPARTMENT_PRESENTATION.otro;
    const Icon = presentation.icon;

    return (
        <article className="flex min-h-72 flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
            <header className={`flex items-start gap-4 border-b px-5 py-5 ${presentation.headerClass}`}>
                <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl shadow-sm ${presentation.iconClass}`}>
                    <Icon aria-hidden="true" size={21} />
                </span>
                <div className="min-w-0 flex-1">
                    <h2 className="text-base font-black leading-6 text-slate-950">
                        {department.nombre}
                    </h2>
                    <p className="mt-1 text-xs font-medium text-slate-600">
                        {users.length
                            ? `${users.length} persona${users.length === 1 ? "" : "s"} asignada${users.length === 1 ? "" : "s"}`
                            : "Departamento preparado para recibir personas"}
                    </p>
                </div>
            </header>

            <div className="flex-1 p-5">
                {department.descripcion && (
                    <p className="mb-4 text-sm leading-6 text-slate-600">
                        {department.descripcion}
                    </p>
                )}

                {users.length ? (
                    <div className="space-y-2.5" aria-label={`Personas de ${department.nombre}`}>
                        {users.map((user) => (
                            <div key={user.id} className="group flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50/80 px-3.5 py-3 transition hover:border-slate-300 hover:bg-white">
                                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm">
                                    <UserRound aria-hidden="true" size={18} />
                                </span>
                                <div className="min-w-0 flex-1">
                                    <div className="flex min-w-0 items-center gap-2">
                                        <p className="truncate text-sm font-bold text-slate-950">{user.nombre}</p>
                                        {user.es_principal && (
                                            <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800">
                                                Principal
                                            </span>
                                        )}
                                    </div>
                                    <p className="truncate text-xs text-slate-500">
                                        {user.cargo || "Sin cargo informado"}
                                        {user.email ? ` · ${user.email}` : ""}
                                    </p>
                                </div>
                                <IconButton
                                    type="button"
                                    icon={X}
                                    size="sm"
                                    disabled={busy}
                                    aria-label={`Quitar a ${user.nombre} de ${department.nombre}`}
                                    title="Quitar del departamento"
                                    className="h-9 w-9 shrink-0 rounded-full text-slate-400 hover:bg-red-50 hover:text-red-600"
                                    onClick={() => onRemoveUser(department, user)}
                                />
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="rounded-2xl border border-dashed border-emerald-200 bg-emerald-50/50 px-5 py-6 text-center">
                        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-emerald-700 shadow-sm">
                            <UsersRound aria-hidden="true" size={21} />
                        </span>
                        <p className="mt-3 text-sm font-bold text-slate-900">Equipo por configurar</p>
                        <p className="mx-auto mt-1 max-w-xs text-xs leading-5 text-slate-600">
                            Asigna a las personas que generan, administran o validan información en esta área.
                        </p>
                    </div>
                )}
            </div>

            <footer className="flex items-center justify-between gap-3 border-t border-slate-100 bg-slate-50/60 px-5 py-4">
                <Button
                    type="button"
                    size="sm"
                    disabled={busy}
                    aria-label={`Agregar persona a ${department.nombre}`}
                    onClick={() => onAddUser(department)}
                    className="min-h-10 rounded-xl bg-emerald-700 px-3.5 hover:bg-emerald-800"
                >
                    <span className="inline-flex items-center gap-1.5">
                        <Plus aria-hidden="true" size={15} />
                        <UserRoundPlus aria-hidden="true" size={16} />
                        Agregar persona
                    </span>
                </Button>
                <IconButton
                    type="button"
                    icon={Trash2}
                    size="sm"
                    disabled={busy}
                    aria-label={`Eliminar departamento ${department.nombre}`}
                    title="Eliminar departamento"
                    className="h-10 w-10 rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm hover:border-red-200 hover:bg-red-50 hover:text-red-600"
                    onClick={() => onDelete(department)}
                />
            </footer>
        </article>
    );
}
