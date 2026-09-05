import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  calculationMethodologyPresentation,
  compatibleDomainTotals,
  domainActivities,
  domainRecords,
  explicitDomainActivities,
  isCalculationSelectable,
  wasteClassification,
} from "./operationSelectors.js";
import {
  eligibilityPresentation,
  evidencePresentation,
  qualityPresentation,
} from "./operationalPresentation.js";

test("Combustibles conserva registros genericos, moviles y estacionarios", () => {
  const records = [
    { flujo: "combustible", actividad_detalle: { id: 1, tipo: "consumo_combustible" } },
    { flujo: "combustible_movil", actividad_detalle: { id: 2, tipo: "consumo_combustible" } },
    { flujo: "combustible_estacionario", actividad_detalle: { id: 3, tipo: "consumo_combustible_estacionario" } },
    { flujo: "agua", actividad_detalle: { id: 4, tipo: "consumo_agua" } },
  ];

  assert.deepEqual(domainRecords(records, "combustibles").map((item) => item.flujo), [
    "combustible", "combustible_movil", "combustible_estacionario",
  ]);
  assert.deepEqual(domainActivities(records, "combustibles").map((item) => item.id), [1, 2, 3]);
});

test("actividades explícitas de viajes se validan y deduplican sin inventar IDs", () => {
  const activity = {
    id: 77,
    codigo: "VIAJE-77",
    nombre: "Viaje Bodega → Obra",
    tipo: "transporte",
  };
  assert.deepEqual(explicitDomainActivities([
    activity,
    { ...activity },
    { nombre: "Sin ID", tipo: "transporte" },
    { id: 88, nombre: "Energía", tipo: "consumo_energia" },
  ], "transporte"), [activity]);
  assert.deepEqual(explicitDomainActivities([], "transporte"), []);
});

test("otros dominios conservan actividades derivadas de registros ambientales", () => {
  const activity = { id: 14, tipo: "consumo_energia", nombre: "Consumo" };
  assert.deepEqual(domainActivities([{ actividad_detalle: activity }], "energia"), [activity]);
});

test("clasifica residuos nuevos y conserva lectura de históricos", () => {
  const newNonHazardous = [
    { clasificacion_residuo: "no_peligroso", tipo_recurso: "" },
    { clasificacion_residuo: "no_peligroso", tipo_recurso: "madera" },
  ];
  const newHazardous = { clasificacion_residuo: "peligroso", tipo_recurso: "" };
  const legacyNonHazardous = { clasificacion_residuo: "", tipo_recurso: "no_peligroso" };
  const legacyHazardous = { clasificacion_residuo: "", tipo_recurso: "peligroso" };
  const unclassifiedLegacyResource = { clasificacion_residuo: "", tipo_recurso: "madera" };

  assert.equal(newNonHazardous.filter((record) => wasteClassification(record) === "no_peligroso").length, 2);
  assert.equal(newNonHazardous.filter((record) => wasteClassification(record) === "peligroso").length, 0);
  assert.equal(wasteClassification(newHazardous), "peligroso");
  assert.equal(wasteClassification(legacyNonHazardous), "no_peligroso");
  assert.equal(wasteClassification(legacyHazardous), "peligroso");
  assert.equal(wasteClassification(unclassifiedLegacyResource), null);
});

test("el KPI usa totales compatibles del backend y mantiene unidades separadas", () => {
  const indicators = {
    flujos: [
      { flujo: "combustible_movil", concepto: "combustible_consumido" },
      { flujo: "combustible_estacionario", concepto: "combustible_consumido" },
    ],
    totales_compatibles: [
      { concepto: "combustible_consumido", unidad: "L", total: 300 },
      { concepto: "combustible_consumido", unidad: "kg", total: 25 },
      { concepto: "consumo_agua", unidad: "m3", total: 10 },
    ],
  };

  assert.deepEqual(compatibleDomainTotals(indicators, "combustibles"), [
    { concepto: "combustible_consumido", unidad: "L", total: 300 },
    { concepto: "combustible_consumido", unidad: "kg", total: 25 },
  ]);
});

test("presenta metodología candidata bloqueada sin habilitar cálculo", () => {
  const eligibility = {
    estado: "no_calculable",
    metodologia_seleccionada: null,
    metodologia_candidata: { id: 7, nombre: "Combustible Construcción", version: 1 },
    motivos: ["El respaldo presentó un fallo técnico."],
  };

  assert.deepEqual(calculationMethodologyPresentation(eligibility), {
    methodology: eligibility.metodologia_candidata,
    label: null,
  });
  assert.equal(isCalculationSelectable(eligibility), false);
  assert.notEqual(
    calculationMethodologyPresentation(eligibility).methodology.nombre,
    "Sin metodología",
  );
});

test("distingue ambigüedad metodológica y ausencia real de metodología", () => {
  assert.deepEqual(
    calculationMethodologyPresentation({ requiere_revision_metodologica: true }),
    { methodology: null, label: "Revisión metodológica requerida" },
  );
  assert.deepEqual(calculationMethodologyPresentation({}), {
    methodology: null,
    label: "Sin metodología",
  });
});

test("traduce bloqueos documentales a mensajes breves sin nombres internos", () => {
  const technical = eligibilityPresentation({
    estado: "no_calculable",
    motivos: ["combustible_consumido no puede calcularse: el procesamiento del respaldo presentó un fallo técnico"],
  });
  assert.deepEqual(technical, {
    label: "Requiere revisión",
    tone: "warning",
    message: "El respaldo no pudo procesarse. Puedes revisarlo o reintentarlo.",
  });
  assert.equal(technical.message.includes("combustible_consumido"), false);
  assert.equal(
    eligibilityPresentation({ estado: "calculable_completo" }).message,
    "Metodología y factor disponibles.",
  );
  const outsideWork = eligibilityPresentation({ estado: "no_calculable", motivos: ["El registro es anterior al inicio de la obra"] });
  assert.equal(outsideWork.label, "No calculable");
  assert.equal(outsideWork.message, "El registro es anterior al inicio de la obra");
});

test("resume todos los estados documentales requeridos sin cambiar el contrato", () => {
  const cases = [
    ["revision_tecnica", "El respaldo no pudo procesarse."],
    ["observada", "El respaldo tiene observaciones pendientes."],
    ["contradiccion", "El respaldo presenta diferencias con el dato registrado."],
    ["no_pertinente", "El archivo adjunto no corresponde al respaldo esperado."],
    ["compatible_incompleta", "El respaldo es compatible, pero está incompleto."],
  ];
  for (const [estado, message] of cases) {
    const item = {
      estado: "requiere_revision",
      observacion_detalle: {
        evidencia: { validacion_documental: { estado } },
      },
    };
    const original = structuredClone(item);
    assert.equal(qualityPresentation(item).message, message);
    assert.deepEqual(item, original);
  }

  assert.equal(
    qualityPresentation({ estado: "confiable_con_observaciones", observacion_detalle: { evidencia: null } }).message,
    "Dato manual sin respaldo documental.",
  );
  assert.equal(
    qualityPresentation({
      estado: "confiable_con_observaciones",
      observacion_detalle: { evidencia: { estado_documental: "pendiente" } },
    }).message,
    "Respaldo adjunto, pendiente de validación.",
  );
});

test("la tabla conserva identidad y estado del respaldo sin comparaciones campo a campo", () => {
  const evidence = {
    nombre: "Vale de combustible",
    validacion_documental: {
      estado: "contradiccion",
      comparaciones: [{ campo: "cantidad", declarado: 250, documental: 200 }],
    },
  };
  assert.equal(evidencePresentation(evidence).label, "Contradice el dato");

  const component = readFileSync(
    new URL("../components/DomainQualityPanel.jsx", import.meta.url),
    "utf8",
  );
  assert.match(component, /evidence\.nombre/);
  assert.doesNotMatch(component, /comparaciones\?\.map|comparison\.declarado|comparison\.documental/);
});

test("captura manual usa fecha explícita, fuentes scoped y alcance de obra por defecto", () => {
  const modal = readFileSync(
    new URL("../components/ManualFlowRecordModal.jsx", import.meta.url),
    "utf8",
  );
  const api = readFileSync(
    new URL("../api/activityApi.js", import.meta.url),
    "utf8",
  );

  assert.match(modal, /label="Fecha del registro"/);
  assert.match(modal, /`\$\{form\.recordDate\}T12:00:00`/);
  assert.doesNotMatch(modal, /new Date\(\)\.toISOString/);
  assert.match(modal, /Alcance del registro/);
  assert.match(modal, /Toda la obra/);
  assert.match(modal, /Especificar punto de medición/);
  assert.match(modal, /value="sistema_externo"/);
  assert.doesNotMatch(modal, /value="integracion"/);
  assert.match(api, /dominio: domain/);
});

test("captura manual obtiene taxonomía de respaldo por flujo y limpia incompatibles", () => {
  const modal = readFileSync(
    new URL("../components/ManualFlowRecordModal.jsx", import.meta.url),
    "utf8",
  );
  const api = readFileSync(
    new URL("../api/sectorFlowsApi.js", import.meta.url),
    "utf8",
  );

  assert.match(modal, /listEvidenceTypes\(sourceDomain\)/);
  assert.match(modal, /label="Tipo de respaldo"/);
  assert.match(modal, /setEvidenceTypes\(options\)/);
  assert.match(modal, /evidenceType:\s*options\.some/);
  assert.doesNotMatch(modal, /<option value="boleta_electrica">/);
  assert.doesNotMatch(modal, /<option value="factura_combustible">/);
  assert.match(api, /\/tipos-evidencia\//);
  assert.match(api, /dominio: domain/);
});

test("calidad omite destino sin clasificar pero conserva destinos reales", () => {
  const panel = readFileSync(
    new URL("../components/DomainQualityPanel.jsx", import.meta.url),
    "utf8",
  );

  assert.match(panel, /destination !== "sin_clasificar"/);
  assert.match(panel, /human\(\s*destination/);
});

test("indicadores de obra muestran todos los dominios sin sumar en React", () => {
  const page = readFileSync(
    new URL("../../obras/pages/ObraIndicatorsPage.jsx", import.meta.url),
    "utf8",
  );

  assert.match(page, /availableIndicators\.map/);
  assert.doesNotMatch(page, /availableIndicators\.slice\(0, 4\)/);
  assert.match(page, /indicator\.valor_actual/);
  assert.match(page, /state\.impacts\.slice/);
  assert.doesNotMatch(page, /reduce\([^)]*valor/);
});

test("agua presenta uso operacional neutral sin afectar el cálculo de otros dominios", () => {
  const panel = readFileSync(
    new URL("../components/DomainCalculationPanel.jsx", import.meta.url),
    "utf8",
  );

  assert.match(panel, /\["agua", "residuos"\]\.includes\(domain\)/);
  assert.match(panel, /title="Sin cálculo asociado"/);
  assert.match(panel, /se utiliza directamente en indicadores ambientales/);
  assert.match(panel, /Calcular/);
});

test("residuos presenta material, cantidad y destino sin códigos internos", () => {
  const qualityPanel = readFileSync(
    new URL("../components/DomainQualityPanel.jsx", import.meta.url),
    "utf8",
  );
  const wastePage = readFileSync(
    new URL("../pages/WastePage.jsx", import.meta.url),
    "utf8",
  );

  assert.match(wastePage, /wasteClassification\(record\) === "no_peligroso"/);
  assert.match(wastePage, /wasteClassification\(record\) === "peligroso"/);
  assert.match(qualityPanel, /record\.tipo_residuo === "otro"/);
  assert.match(qualityPanel, /disposicion: "Disposición final"/);
  assert.match(qualityPanel, /wasteType/);
  assert.match(qualityPanel, /observedValue/);
  assert.match(qualityPanel, /wasteClassification/);
});

test("residuos separa clasificación, tipo gobernado y destino", () => {
  const modal = readFileSync(
    new URL("../components/ManualFlowRecordModal.jsx", import.meta.url),
    "utf8",
  );
  const api = readFileSync(
    new URL("../api/sectorFlowsApi.js", import.meta.url),
    "utf8",
  );

  assert.match(modal, /label="Clasificación"/);
  assert.match(modal, /label="Tipo de residuo"/);
  assert.match(modal, /listWasteTypes\(\)/);
  assert.match(modal, /clasificacion_residuo/);
  assert.match(modal, /tipo_residuo/);
  assert.match(modal, /Destino pendiente de definir/);
  assert.match(api, /\/tipos-residuo\//);
  assert.doesNotMatch(modal, /label: "Residuo no peligroso"/);
  assert.doesNotMatch(modal, /label: "Residuo peligroso"/);
});

test("residuos traduce el dominio UI al flujo persistido sin cambiar catálogos", () => {
  const modal = readFileSync(
    new URL("../components/ManualFlowRecordModal.jsx", import.meta.url),
    "utf8",
  );

  assert.match(modal, /residuos:\s*\{\s*flow:\s*"residuo"/);
  assert.match(modal, /append\("flujo", selectedMode\?\.flow \|\| config\.flow \|\| domain\)/);
  assert.match(modal, /const sourceDomain = selectedMode\?\.flow \|\| domain/);
  assert.match(modal, /listDataSources\(organizationId, sourceDomain\)/);
  assert.match(modal, /listEvidenceTypes\(sourceDomain\)/);
});

test("Transporte entrega actividades reales de viajes al panel de cálculo", () => {
  const transportPage = readFileSync(new URL("../pages/TransportPage.jsx", import.meta.url), "utf8");
  const calculationPanel = readFileSync(
    new URL("../components/DomainCalculationPanel.jsx", import.meta.url),
    "utf8",
  );

  assert.match(transportPage, /journey\.actividad_detalle/);
  assert.match(transportPage, /activities=\{transportActivities\}/);
  assert.match(calculationPanel, /activities: activitiesOverride/);
  assert.match(calculationPanel, /activitiesOverride === undefined/);
  assert.match(calculationPanel, /getActivityEligibility/);
  assert.match(calculationPanel, /getActivityCalculations/);
  assert.match(calculationPanel, /calculateActivity/);
});

test("Materiales entrega actividades reales de eventos al panel de cálculo", () => {
  const materialsPage = readFileSync(new URL("../pages/MaterialsPage.jsx", import.meta.url), "utf8");
  const reception = { id: 11, tipo: "movimiento_material" };
  const use = { id: 12, tipo: "movimiento_material" };
  assert.deepEqual(explicitDomainActivities([reception, use], "materiales"), [reception, use]);
  assert.deepEqual(explicitDomainActivities([reception, reception], "materiales"), [reception]);
  assert.deepEqual(explicitDomainActivities([{ id: 13, tipo: "transporte" }], "materiales"), []);
  assert.deepEqual(explicitDomainActivities([], "materiales"), []);
  assert.match(materialsPage, /event\.actividad_detalle/);
  assert.match(materialsPage, /activities=\{materialActivities\}/);
  assert.doesNotMatch(materialsPage, /RegistroFlujoAmbiental/);
});

test("elegibilidad distingue candidato bloqueado, no aplicable y revisión real", () => {
  const blocked = eligibilityPresentation({
    estado: "no_calculable",
    metodologia_candidata: { id: 7, nombre: "Material recibido", version: 1 },
    motivos: ["No existe un factor ambiental gobernado aplicable a Cemento Portland."],
  });
  assert.deepEqual(blocked, {
    label: "No calculable", tone: "neutral",
    message: "No existe un factor ambiental gobernado aplicable a Cemento Portland.",
  });
  assert.deepEqual(
    eligibilityPresentation({ estado: "no_aplicable", motivos: ["Este movimiento no es un punto contable de la metodología de material recibido."] }),
    { label: "No aplica", tone: "neutral", message: "Este movimiento no es un punto contable de la metodología de material recibido." },
  );
  assert.equal(eligibilityPresentation({ estado: "requiere_revision", motivos: [] }).label, "Requiere revisión");
});
