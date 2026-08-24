import assert from "node:assert/strict";
import test from "node:test";

import { clearSessionNavigationContext } from "./sessionNavigation.js";

test("logout elimina organización y workspace de la identidad anterior", () => {
  const values = new Map([
    ["carbono_zero.activeOrganizacionId", "tenant-X"],
    ["carbono_zero.operationalWorkspaceId", "workspace-X"],
    ["carbono_zero.theme", "dark"],
  ]);
  clearSessionNavigationContext({ removeItem: (key) => values.delete(key) });

  assert.equal(values.has("carbono_zero.activeOrganizacionId"), false);
  assert.equal(values.has("carbono_zero.operationalWorkspaceId"), false);
  assert.equal(values.get("carbono_zero.theme"), "dark");
});
