import aserraderoPreset from "../aserradero/preset";

const forestalPreset = {
  ...aserraderoPreset,
  key: "forestal",
  name: "Forestal",
  dashboardTitle: "Dashboard forestal",
  navigationProfile: { ...aserraderoPreset.navigationProfile, processesLabel: "Procesos forestales" },
  navigationExtensions: aserraderoPreset.navigationExtensions,
};

export default forestalPreset;
