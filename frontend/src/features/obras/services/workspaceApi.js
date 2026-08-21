import { api } from "@/shared/services/api";
import {
  getBaselines,
  getEnvironmentalImpacts,
  getIndicators,
} from "@/features/operacion/api/calculationApi";

import {
  getComplianceSummary,
} from "@/features/compliance/api/complianceApi";

const rows = (value) => (Array.isArray(value) ? value : value?.results || []);
const base = (organizationId, workId) =>
  `/organizaciones/${encodeURIComponent(organizationId)}/obras/${encodeURIComponent(workId)}`;
const routeId = (work) => work?.id || work?.obra_id || work?.codigo_obra;

async function resolveWork(organizationId, workOrRouteId) {
  if (workOrRouteId && typeof workOrRouteId === "object") {
    return workOrRouteId;
  }
  const works = await getOrganizationWorks(organizationId);
  const work = works.find((item) =>
    [item.id, item.obra_id, item.codigo_obra].some((value) => String(value) === String(workOrRouteId)),
  );
  if (!work) {
    const error = new Error("No se encontró la obra");
    error.response = { status: 404 };
    throw error;
  }
  return work;
}

export async function getOrganizationWorks(organizationId) {
  return rows((await api.get(`/organizaciones/${encodeURIComponent(organizationId)}/obras/`)).data);
}

export async function createOrganizationWork(organizationId, payload) {
  return (await api.post(`/organizaciones/${encodeURIComponent(organizationId)}/obras/`, {
    ...payload,
    organizacion_id: organizationId,
  })).data;
}

export async function getWorkContext(organizationId, workOrRouteId) {
  const work = await resolveWork(organizationId, workOrRouteId);
  const workId = work.id || work.obra_id;
  const context = await api.get(`${base(organizationId, workId)}/contexto/`);
  return { obra: { ...work, ...context.data?.obra }, context: context.data };
}

export async function getWorkWorkspace(
  organizationId,
  workRouteId,
) {
  const work = await resolveWork(
    organizationId,
    workRouteId,
  );

  const workId =
    work.id ||
    work.obra_id;

  const params = {
    obra: workId,
  };

  const [
    contextResult,
    timelineResult,
    indicatorsResult,
    governedIndicatorsResult,
    baselinesResult,
    impactsResult,
    complianceResult,
  ] = await Promise.allSettled([
    api.get(
      `${base(
        organizationId,
        workId,
      )}/contexto/`,
    ),

    api.get(
      `${base(
        organizationId,
        workId,
      )}/timeline/`,
    ),

    api.get(
      `${base(
        organizationId,
        workId,
      )}/indicadores/`,
    ),

    getIndicators(
      organizationId,
      params,
    ),

    getBaselines(
      organizationId,
      params,
    ),

    getEnvironmentalImpacts(
      organizationId,
      params,
    ),

    getComplianceSummary(
      organizationId,
      params,
    ),
  ]);

  if (
    contextResult.status ===
    "rejected"
  ) {
    throw contextResult.reason;
  }

  const context =
    contextResult.value.data;

  return {
    obra: {
      ...work,
      ...context?.obra,
    },

    context,

    timeline:
      timelineResult.status ===
        "fulfilled"
        ? timelineResult.value.data
        : null,

    indicators:
      indicatorsResult.status ===
        "fulfilled"
        ? indicatorsResult.value.data
        : null,

    governedIndicators:
      governedIndicatorsResult.status ===
        "fulfilled"
        ? governedIndicatorsResult.value
        : [],

    baselines:
      baselinesResult.status ===
        "fulfilled"
        ? baselinesResult.value
        : [],

    impacts:
      impactsResult.status ===
        "fulfilled"
        ? impactsResult.value
        : [],

    compliance:
      complianceResult.status ===
        "fulfilled"
        ? complianceResult.value
        : null,

    resourceErrors: {
      timeline:
        timelineResult.status ===
        "rejected",

      indicators:
        indicatorsResult.status ===
        "rejected",

      governedIndicators:
        governedIndicatorsResult.status ===
        "rejected",

      baselines:
        baselinesResult.status ===
        "rejected",

      impacts:
        impactsResult.status ===
        "rejected",

      compliance:
        complianceResult.status ===
        "rejected",
    },

    routeId:
      routeId(work),
  };
}
