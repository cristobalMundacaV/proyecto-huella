import { applicability, capabilityKeyForDomain } from "../features/operacion/utils/operationSelectors.js";

/** Decides which children of the obra "Operación" nav item (from
 * `getUnifiedNavigation` in obra scope) are visible and what mini status
 * each keeps — the RBAC-vs-configuration distinction: a flow whose
 * applicability is `no_aplica` (organization or obra explicitly said it
 * doesn't apply) is dropped; a flow still `pendiente` stays visible with a
 * "needs configuration" dot. RBAC itself is handled separately by
 * `filterNavigation` before this ever runs. The whole "Gestión" item is
 * outside this filter and always remains available. */
export function withObraFlowStates(navigation, applicabilityRows = []) {
  const fakeContext = { diagnostico_obra: { aplicabilidad: applicabilityRows } };
  return {
    ...navigation,
    groups: navigation.groups.map((group) => ({
      ...group,
      items: group.items.map((item) => {
        if (item.id !== "operation" || !item.children) return item;
        return {
          ...item,
          children: item.children
            .map((child) => {
              return { ...child, state: applicability(fakeContext, capabilityKeyForDomain(child.domain)) };
            })
            .filter((child) => child.state !== "no_aplica"),
        };
      }),
    })),
  };
}
