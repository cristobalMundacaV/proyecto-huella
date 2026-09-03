import assert from "node:assert/strict";
import test from "node:test";

import { humanizeApiError } from "./apiErrors.js";

test("traduce errores HTTP de autorización y recurso", () => {
  assert.equal(humanizeApiError({ response: { status: 403 } }), "No tienes permisos para realizar esta acción.");
  assert.equal(humanizeApiError({ response: { status: 404 } }), "No encontramos el recurso solicitado o ya no está disponible.");
});

test("conserva detalles del dominio y presenta validaciones por campo", () => {
  assert.equal(humanizeApiError({ response: { status: 400, data: { detail: "La transición requiere una reevaluación." } } }), "La transición requiere una reevaluación.");
  assert.equal(humanizeApiError({ response: { status: 400, data: { estado: ["No es válido."] } } }), "Estado: No es válido.");
});

test("traduce campos obligatorios de DRF", () => {
  const error = { response: { status: 400, data: { codigo: ["This field is required."] } } };
  assert.equal(humanizeApiError(error), "Código: Este campo es obligatorio.");
});
