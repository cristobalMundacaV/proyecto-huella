import aserraderoPreset from "../aserradero/preset";

const forestalPreset = {
  ...aserraderoPreset,
  key: "forestal",
  name: "Forestal",
  dashboardTitle: "Dashboard forestal",
  navigation: aserraderoPreset.navigation.filter((item) => item.view !== "operacion"),
};

export default forestalPreset;
