import {
    Plus,
    Trash2,
    UserRound,
} from "lucide-react";

import {
    Button,
} from "@/shared/ui";

import {
    DEPARTMENT_PRESENTATION,
} from "../config/departmentPresentation";

export default function DepartmentCard({
    department,
    users = [],
    onAddUser,
    onDelete,
}) {
    const presentation =
        DEPARTMENT_PRESENTATION[
        department.tipo
        ] ||
        DEPARTMENT_PRESENTATION.otro;

    const Icon =
        presentation.icon;

    return (
        <article
            className="
                overflow-hidden
                rounded-2xl
                border
                border-slate-200
                bg-white
                shadow-sm
            "
        >
            <header
                className={`
                    flex
                    items-center
                    justify-between
                    border-b
                    p-5
                    ${presentation.headerClass}
                `}
            >
                <div
                    className="
                        flex
                        items-center
                        gap-3
                    "
                >
                    <span
                        className={`
                            flex
                            h-11
                            w-11
                            items-center
                            justify-center
                            rounded-xl
                            ${presentation.iconClass}
                        `}
                    >
                        <Icon
                            size={21}
                        />
                    </span>

                    <div>
                        <h3
                            className="
                                font-semibold
                                text-slate-900
                            "
                        >
                            {
                                department.nombre
                            }
                        </h3>

                        {department.descripcion && (
                            <p
                                className="
                                    mt-1
                                    text-xs
                                    text-slate-600
                                "
                            >
                                {
                                    department.descripcion
                                }
                            </p>
                        )}
                    </div>
                </div>

                <button
                    type="button"
                    onClick={() =>
                        onDelete(
                            department,
                        )
                    }
                    className="
                        rounded-lg
                        p-2
                        text-slate-400
                        hover:bg-white/70
                        hover:text-red-600
                    "
                >
                    <Trash2
                        size={17}
                    />
                </button>
            </header>

            <div
                className="
                    space-y-3
                    p-5
                "
            >
                {users.map(
                    (user) => (
                        <div
                            key={
                                user.id
                            }
                            className="
                                flex
                                items-center
                                gap-3
                                rounded-xl
                                border
                                border-slate-200
                                bg-slate-50
                                px-4
                                py-3
                            "
                        >
                            <span
                                className="
                                    flex
                                    h-9
                                    w-9
                                    shrink-0
                                    items-center
                                    justify-center
                                    rounded-full
                                    bg-white
                                    text-slate-600
                                    shadow-sm
                                "
                            >
                                <UserRound
                                    size={17}
                                />
                            </span>

                            <div
                                className="
                                    min-w-0
                                "
                            >
                                <div
                                    className="
                                        truncate
                                        text-sm
                                        font-semibold
                                        text-slate-900
                                    "
                                >
                                    {
                                        user.nombre
                                    }
                                </div>

                                <div
                                    className="
                                        truncate
                                        text-xs
                                        text-slate-500
                                    "
                                >
                                    {
                                        user.cargo ||
                                        "Sin cargo informado"
                                    }
                                </div>
                            </div>
                        </div>
                    ),
                )}

                {!users.length && (
                    <div
                        className="
                            rounded-xl
                            border
                            border-dashed
                            border-slate-200
                            px-4
                            py-6
                            text-center
                            text-sm
                            text-slate-500
                        "
                    >
                        Aún no hay personas
                        asignadas.
                    </div>
                )}

                <Button
                    type="button"
                    variant="secondary"
                    onClick={() =>
                        onAddUser(
                            department,
                        )
                    }
                >
                    <Plus
                        size={16}
                    />

                    Agregar persona
                </Button>
            </div>
        </article>
    );
}