import { api } from "@/shared/services/api";

const base = (organizationId) =>
    `/organizaciones/${encodeURIComponent(
        organizationId,
    )}`;

export async function getDepartments(
    organizationId,
) {
    return (
        await api.get(
            `${base(
                organizationId,
            )}/areas-operacionales/`,
        )
    ).data;
}

export async function createDepartment(
    organizationId,
    payload,
) {
    return (
        await api.post(
            `${base(
                organizationId,
            )}/areas-operacionales/`,
            payload,
        )
    ).data;
}

export async function updateDepartment(
    organizationId,
    departmentId,
    payload,
) {
    return (
        await api.patch(
            `${base(
                organizationId,
            )}/areas-operacionales/${departmentId}/`,
            payload,
        )
    ).data;
}

export async function deleteDepartment(
    organizationId,
    departmentId,
) {
    return api.delete(
        `${base(
            organizationId,
        )}/areas-operacionales/${departmentId}/`,
    );
}

export async function getDepartmentUsers(
    organizationId,
    departmentId,
) {
    return (
        await api.get(
            `${base(
                organizationId,
            )}/areas-operacionales/${departmentId}/usuarios/`,
        )
    ).data;
}

export async function addDepartmentUser(
    organizationId,
    departmentId,
    payload,
) {
    return (
        await api.post(
            `${base(
                organizationId,
            )}/areas-operacionales/${departmentId}/usuarios/`,
            payload,
        )
    ).data;
}

export async function removeDepartmentUser(
    organizationId,
    departmentId,
    assignmentId,
) {
    return api.delete(
        `${base(
            organizationId,
        )}/areas-operacionales/${departmentId}/usuarios/${assignmentId}/`,
    );
}