import aserraderoPreset from "./aserradero/preset";
import construccionPreset from "./construccion/preset";
import forestalPreset from "./forestal/preset";
import industrialPreset from "./industrial/preset";
import transportePreset from "./transporte/preset";

export const DEFAULT_PRESET_KEY = "construccion";
export const PRESET_STORAGE_KEY = "carbono_zero.activePreset";

export const presets = {
  [construccionPreset.key]: construccionPreset,
  [aserraderoPreset.key]: aserraderoPreset,
  [forestalPreset.key]: forestalPreset,
  [transportePreset.key]: transportePreset,
  [industrialPreset.key]: industrialPreset,
};

export function getPreset(key = DEFAULT_PRESET_KEY) {
  return presets[key] || presets[DEFAULT_PRESET_KEY];
}

export function getPresetLabel(key = DEFAULT_PRESET_KEY) {
  return getPreset(key).name;
}

export function getActivePreset(key = null) {
  if (key) {
    return getPreset(key);
  }

  if (typeof window === "undefined") {
    return getPreset();
  }

  return getPreset(window.localStorage.getItem(PRESET_STORAGE_KEY) || DEFAULT_PRESET_KEY);
}

export const activePreset = getPreset(DEFAULT_PRESET_KEY);
