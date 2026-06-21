import { useMemo } from "react";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";

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
  const { activeConstructora } = useConstructoraActiva();

  return useMemo(() => {
    const matrixKey = resolveEnvironmentalPresetKey(activeConstructora);
    const matrix = resolveEnvironmentalPreset(activeConstructora);

    return {
      activeCompany: activeConstructora,
      matrix,
      matrixKey,
    };
  }, [activeConstructora]);
}
