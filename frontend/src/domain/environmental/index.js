import { useMemo } from "react";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  DEFAULT_ENVIRONMENTAL_MATRIX_KEY,
  environmentalPresetMatrix,
} from "./environmentalPresetMatrix.js";
import {
  resolveEnvironmentalPreset,
  resolveEnvironmentalPresetKey,
} from "./environmentalPresetResolver.js";

export {
  DEFAULT_ENVIRONMENTAL_MATRIX_KEY,
  environmentalPresetMatrix,
  resolveEnvironmentalPreset,
  resolveEnvironmentalPresetKey,
};

export function useEnvironmentalContext() {
  const { activeOrganizacion } = useOrganizacionActiva();

  return useMemo(() => {
    const matrixKey = resolveEnvironmentalPresetKey(activeOrganizacion);
    const matrix = resolveEnvironmentalPreset(activeOrganizacion);

    return {
      activeCompany: activeOrganizacion,
      matrix,
      matrixKey,
    };
  }, [activeOrganizacion]);
}
