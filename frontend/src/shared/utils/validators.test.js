import assert from "node:assert/strict";
import test from "node:test";
import { formatChileanPhone, formatChileanRut, isValidChileanRut, isValidEmail, isValidPhone } from "./validators.js";

test("valida correo y permite un valor opcional vacío", () => { assert.equal(isValidEmail("persona@empresa.cl"), true); assert.equal(isValidEmail("persona@empresa"), false); assert.equal(isValidEmail(""), true); });
test("acepta formatos móviles chilenos y rechaza valores incompletos", () => { ["+56 9 1234 5678", "+56912345678", "9 1234 5678", "912345678"].forEach((value) => assert.equal(isValidPhone(value), true)); assert.equal(isValidPhone("123"), false); assert.equal(isValidPhone(""), true); assert.equal(formatChileanPhone("912345678"), "+56 9 1234 5678"); });
test("valida y formatea el RUT chileno existente", () => { assert.equal(formatChileanRut("216832647"), "21.683.264-7"); assert.equal(isValidChileanRut("21.683.264-7"), true); assert.equal(isValidChileanRut("21.683.264-8"), false); });
