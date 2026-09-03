import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { resolveAppLoginUrl } from "./landingConfig.js";

test("el acceso de la landing apunta al login del host de plataforma", () => {
  assert.equal(
    resolveAppLoginUrl("https://app.carbonozero.mundacasolutions.com"),
    "https://app.carbonozero.mundacasolutions.com/login",
  );
  assert.equal(resolveAppLoginUrl("https://app.example.com/"), "https://app.example.com/login");
  assert.equal(resolveAppLoginUrl(""), "/app");
});

test("Vite lee variables públicas desde el env canónico del repositorio", () => {
  const viteConfig = readFileSync(new URL("../../vite.config.js", import.meta.url), "utf8");
  const exampleEnv = readFileSync(new URL("../../../.env.example", import.meta.url), "utf8");

  assert.match(viteConfig, /envDir: path\.resolve\(__dirname, "\.\."\)/);
  assert.match(exampleEnv, /^VITE_APP_URL=https:\/\/app\.carbonozero\.mundacasolutions\.com$/m);
  assert.match(exampleEnv, /^VITE_API_URL=\/api$/m);
});
