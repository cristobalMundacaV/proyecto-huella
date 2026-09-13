import { applicability, capabilityKeyForDomain } from "../features/operacion/utils/operationSelectors.js";

/** Decides which items of the obra "OBRA ACTIVA" subnav (from
 * `getObraContextualSubnav`) are visible and what mini status each keeps —
 * the RBAC-vs-configuration distinction: a flow whose applicability is
 * `no_aplica` (organization or obra explicitly said it doesn't apply) is
 * dropped; a flow still `pendiente` stays visible with a "needs
 * configuration" dot; RBAC itself is handled separately by
 * `filterNavigation` before this ever runs. "Resumen operacional" and the
 * "Gestión" group are never gated by applicability — they always show. */
export function withObraFlowStates(subnav, applicabilityRows = []) {
  const fakeContext = { diagnostico_obra: { aplicabilidad: applicabilityRows } };
  return {
    ...subnav,
    groups: subnav.groups.map((group) => ({
      ...group,
      items: group.items
        .map((item) => {
          if (group.id !== "operation" || item.id === "operationOverview") return { ...item, state: "always" };
          return { ...item, state: applicability(fakeContext, capabilityKeyForDomain(item.domain)) };
        })
        .filter((item) => item.state !== "no_aplica"),
    })),
  };
}
