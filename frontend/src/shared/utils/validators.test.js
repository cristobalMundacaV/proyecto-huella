import assert from "node:assert/strict";
import test from "node:test";
import { formatChileanPhone, formatChileanRut, isValidChileanRut, isValidEmail, isValidPhone } from "./validators.js";

test("valida correo y permite un valor opcional vacío", () => { assert.equal(isValidEmail("persona@empresa.cl"), true); assert.equal(isValidEmail("persona@empresa"), false); assert.equal(isValidEmail(""), true); });
test("acepta formatos móviles chilenos y rechaza valores incompletos", () => { ["+56 9 1234 5678", "+56912345678", "9 1234 5678", "912345678"].forEach((value) => assert.equal(isValidPhone(value), true)); assert.equal(isValidPhone("123"), false); assert.equal(isValidPhone(""), true); assert.equal(formatChileanPhone("912345678"), "+56 9 1234 5678"); });
test("acepta y formatea números fijos chilenos", () => { ["+56 41 245 7810", "+56412457810", "41 245 7810", "412457810", "+56 2 2345 6789"].forEach((value) => assert.equal(isValidPhone(value), true)); assert.equal(formatChileanPhone("412457810"), "+56 41 245 7810"); assert.equal(formatChileanPhone("223456789"), "+56 2 2345 6789"); assert.equal(isValidPhone("112345678"), false); });
test("valida y formatea el RUT chileno existente", () => { assert.equal(formatChileanRut("216832647"), "21.683.264-7"); assert.equal(isValidChileanRut("21.683.264-7"), true); assert.equal(isValidChileanRut("21.683.264-8"), false); });
