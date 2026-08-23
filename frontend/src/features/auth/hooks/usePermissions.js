import { useCallback, useMemo } from "react";

import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

export function usePermissions() {
  const { user } = useAuth();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const membership = useMemo(
    () => user?.organizaciones?.find((item) => String(item.organizacion_id) === String(activeOrganizacionId)) || null,
    [activeOrganizacionId, user]
  );
  const permissions = useMemo(() => new Set(membership?.permissions || []), [membership]);
  const can = useCallback(
    (permission) => Boolean(user?.is_superuser || permissions.has(permission)),
    [permissions, user?.is_superuser]
  );
  return { can, membership, permissions };
}
