import {
    useCallback,
    useEffect,
    useState,
} from "react";

import {
    Plus,
    UsersRound,
} from "lucide-react";

import {
    Button,
    ErrorState,
} from "@/shared/ui";

import {
    useOrganizacionActiva,
} from "@/features/organizaciones/context/OrganizacionActivaContext";

import DepartmentCard
    from "../components/DepartmentCard";

import {
    deleteDepartment,
    getDepartmentUsers,
    getDepartments,
} from "../api/organizationStructureApi";

export default function OrganizationStructurePage() {
    const {
        activeOrganizacionId,
    } =
        useOrganizacionActiva();

    const [
        departments,
        setDepartments,
    ] = useState([]);

    const [
        usersByDepartment,
        setUsersByDepartment,
    ] = useState({});

    const [
        loading,
        setLoading,
    ] = useState(true);

    const [
        error,
        setError,
    ] = useState("");
    const load = useCallback(async () => {
        if (!activeOrganizacionId) {
            setDepartments([]);
            setUsersByDepartment({});
            setLoading(false);
            return;
        }

        setLoading(true);
        setError("");

        try {
            const data =
                await getDepartments(
                    activeOrganizacionId,
                );

            const active =
                data.filter(
                    (department) =>
                        department.activa,
                );

            setDepartments(
                active,
            );

            const entries =
                await Promise.all(
                    active.map(
                        async (
                            department,
                        ) => [
                                department.id,
                                await getDepartmentUsers(
                                    activeOrganizacionId,
                                    department.id,
                                ),
                            ],
                    ),
                );

            setUsersByDepartment(
                Object.fromEntries(
                    entries,
                ),
            );
        } catch {
            setError(
                "No fue posible cargar la estructura organizacional.",
            );
        } finally {
            setLoading(false);
        }
    }, [activeOrganizacionId]);
    useEffect(() => {
        load();
    }, [load]);

    async function handleDelete(
        department,
    ) {
        await deleteDepartment(
            activeOrganizacionId,
            department.id,
        );

        await load();
    }

    if (error) {
        return (
            <ErrorState
                title="No pudimos cargar la estructura"
                description={error}
                onRetry={load}
            />
        );
    }

    return (
        <section
            className="
                space-y-6
            "
        >
            <header
                className="
                    flex
                    flex-wrap
                    items-start
                    justify-between
                    gap-4
                "
            >
                <div>
                    <div
                        className="
                            mb-2
                            flex
                            items-center
                            gap-2
                            text-emerald-700
                        "
                    >
                        <UsersRound
                            size={20}
                        />

                        <span
                            className="
                                text-xs
                                font-bold
                                uppercase
                                tracking-wider
                            "
                        >
                            Organización
                        </span>
                    </div>

                    <h1
                        className="
                            text-2xl
                            font-bold
                            text-slate-950
                        "
                    >
                        Estructura organizacional
                    </h1>

                    <p
                        className="
                            mt-2
                            max-w-2xl
                            text-sm
                            text-slate-600
                        "
                    >
                        Configura los departamentos
                        y las personas que participan
                        en la operación de la organización.
                    </p>
                </div>

                <Button
                    type="button"
                    disabled={loading}
                >
                    <Plus
                        size={17}
                    />

                    Crear departamento
                </Button>
            </header>

            <div
                className="
                    grid
                    grid-cols-1
                    gap-5
                    xl:grid-cols-2
                "
            >
                {departments.map(
                    (
                        department,
                    ) => (
                        <DepartmentCard
                            key={
                                department.id
                            }
                            department={
                                department
                            }
                            users={
                                usersByDepartment[
                                department.id
                                ] || []
                            }
                            onAddUser={
                                () => { }
                            }
                            onDelete={
                                handleDelete
                            }
                        />
                    ),
                )}
            </div>
        </section>
    );
}