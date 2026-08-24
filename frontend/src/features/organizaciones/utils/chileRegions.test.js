import assert from "node:assert/strict";
import test from "node:test";
import { CHILE_REGIONS, getComunasByRegion, isValidChileLocation } from "./chileRegions.js";

test("incluye las 16 regiones con identidad estable", () => { assert.equal(CHILE_REGIONS.length, 16); assert.equal(new Set(CHILE_REGIONS.map((item) => item.codigo)).size, 16); });
test("Biobío contiene sus comunas y rechaza una comuna de otra región", () => { const region = "Región del Biobío"; assert.equal(getComunasByRegion(region).some((item) => item.nombre === "Concepción"), true); assert.equal(isValidChileLocation(region, "Concepción"), true); assert.equal(isValidChileLocation(region, "Santiago"), false); });
test("aplica las correcciones territoriales requeridas", () => { const names = CHILE_REGIONS.flatMap((item) => item.comunas.map((comuna) => comuna.nombre)); ["Paihuano", "La Calera", "Llay-Llay", "Trehuaco", "Padre Las Casas", "Coyhaique", "Aysén"].forEach((name) => assert.equal(names.includes(name), true)); });
