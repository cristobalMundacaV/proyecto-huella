# EC3 / openEPD — Informe final de macrofase (EC3-01)

Verdict: **IMPLEMENTATION COMPLETE — REAL API VALIDATION PENDING**

No se realizó commit ni push en esta macrofase (explícitamente no autorizado).
Todos los cambios permanecen en el árbol de trabajo local.

## 1. Estado inicial encontrado

Al comenzar esta macrofase, `backend/apps/ec3/` ya contenía una integración
sustancial y no committeada, producida por un proceso concurrente ("Codex")
durante la sesión SOURCE-WATCH anterior: cliente HTTP con rate limiting
compartido en PostgreSQL, modelos de evidencia inmutable, gobernanza de
mapping de materiales (propuesta → revisión humana → promoción → mapping),
proyección estricta del contrato openEPD, hooks de sólo-lectura ya
integrados en `apps.analytics` (selector de factor, calidad, ledger), 8
endpoints DRF, 2 management commands, guards de base de datos por
migración, y una suite de 33-36 tests con fixtures 100% sintéticos. Se
auditó primero (vía un agente de exploración) en vez de asumir o rehacer
nada, cumpliendo el requisito explícito de la misión.

## 2. Trabajo de Codex conservado / corregido

**Conservado sin cambios**: `client.py`, `conf.py`, `checks.py`,
`connector.py`, `models.py`, `rate_limit.py`, `schemas.py`, `apps.py`,
`management/commands/ingest_ec3_epd.py`, `management/commands/
purge_ec3_cache.py`, las 3 migraciones existentes, `tests/fixtures.py`,
`tests/test_client.py`, `tests/test_rate_limit.py`, `tests/
test_governance.py`, y los 3 hooks de sólo-lectura en `apps.analytics`
(`material_factor_selector.py`, `material_quality.py`, `material_ledger.py`).
Todo esto se auditó línea por línea y se consideró correcto, bien
gobernado y coherente con la misión — no se reimplementó nada de esto.

**Corregido** (un bug real encontrado por auditoría, no un rediseño):
`apps/ec3/reporting.py::factor_quality` nunca poblaba `known["standard"]`
(la generación EN 15804), lo que hacía que `material_comparable_sets.
eligibility_chain` (ya existente, de MATERIAL-INTELLIGENCE) reportara
siempre `standard_unknown` para cualquier material mapeado a EC3 —
excluyéndolo permanentemente del motor de comparación/oportunidad ya
existente, sin importar cuán correctamente estuviera revisado, promovido
y mapeado. Se corrigió derivando `standard` del `compliance` real y ya
capturado de la EPD (nunca inventado); si la EPD no declara una generación
EN 15804 explícita, `standard` sigue siendo `None` y el material sigue
correctamente excluido. Ver también `apps/ec3/services.py::ingest_epd`,
donde `RateLimited` ahora se distingue de otros fallos en `SyncRun.message`
(antes se perdía como `ec3_ingestion_failed` genérico, un gap real de
observabilidad).

## 3. Arquitectura final

```
EC3/openEPD → Ec3Client (auth, rate limit, retries, validación estricta)
  → services.ingest_epd → knowledge.ExternalSnapshot/ExternalRecord (versionado, provenance)
  → services.propose_candidate → Review humana → promote_candidate (factor borrador)
  → factor_governance (borrador→pruebas→validado→activo, ya existente)
  → services.propose_mapping → material_factor_mapping (aprobación, ya existente)
  → material_factor_selector (guard EC3 vía factor_block_reason) → CalculoAmbiental
  → material_quality/material_ledger (adaptadores de sólo lectura EC3)
  → [NUEVO] material_comparable_sets/material_hotspots/material_opportunities
    (motor MATERIAL-INTELLIGENCE ya existente, ahora alcanzable por materiales EC3)
  → [NUEVO] apps.ec3.comparability/opportunity (previsualización pre-decisional
    para candidatos EC3 aún no mapeados)
```

Ningún componente nuevo introduce un motor paralelo: cada pieza nueva es o
bien un adaptador delgado sobre autoridades ya existentes (`select_material_
factor`, `evaluate_version`, `unit_conversion.convert_value`, `SyncRun`/
`EnvironmentalSource` de Knowledge Hub), o una capa explícitamente marcada
como pre-decisional que nunca decide nada por sí misma.

## 4. Estado de las 16 áreas de capacidad de la misión

| # | Área | Estado |
|---|---|---|
| 1 | Adapter/client | PASS (Codex) |
| 2 | Ingestión/versionado gobernado | PASS (Codex) |
| 3 | Mapping de materiales gobernado | PASS (Codex) |
| 4 | Elegibilidad científica | PASS (Codex) |
| 5 | Integración con el motor ambiental | PASS (Codex) |
| 6 | Búsqueda/candidatos | PASS (Codex — sin ranking local, por tanto trivialmente determinista) |
| 7 | Capa de comparabilidad | **PASS (esta sesión)** — reutilización directa + previsualización nueva |
| 8 | Motor de oportunidad potencial | **PASS (esta sesión)** — reutilización directa + previsualización nueva |
| 9 | API interna | **PASS (esta sesión)** — 8 endpoints de Codex + 5 nuevos |
| 10 | Refresh/jobs integrados con SOURCE-WATCH | **PASS (esta sesión)** — `refresh_known_ec3_epds`, nunca duplica el mecanismo |
| 11 | Cache/licensing | PASS (Codex) |
| 12 | Seguridad | PASS (Codex, verificado de nuevo esta sesión) |
| 13 | Observabilidad | **PASS (esta sesión)** — `observability.py` + corrección de `ec3_rate_limited` |
| 14 | E2E completo | PASS (Codex, acero estructural) + **extendido esta sesión** hasta comparabilidad cruzada de fuentes |
| 15 | Smoke real | **BLOQUEADO** — `EC3_API_TOKEN` no disponible; procedimiento exacto documentado (única brecha externa permitida) |
| 16 | Documentación | PASS — actualizada esta sesión |

## 5. Archivos creados/modificados esta sesión

Creados: `apps/ec3/comparability.py`, `apps/ec3/opportunity.py`,
`apps/ec3/observability.py`, `apps/ec3/management/commands/
refresh_known_ec3_epds.py`, `apps/ec3/tests/test_comparability_opportunity.py`
(17 tests), `apps/ec3/tests/test_refresh_command.py` (5 tests), `apps/ec3/
tests/test_observability.py` (4 tests).

Modificados: `apps/ec3/services.py` (import de `RateLimited`, distinción de
`ec3_rate_limited` en `SyncRun.message`), `apps/ec3/reporting.py` (`standard`
en `factor_quality`), `apps/ec3/views.py` (imports + 5 vistas nuevas),
`apps/ec3/urls.py` (5 rutas nuevas), `docs/integrations/ec3/03_OPERATIONS.md`,
`docs/integrations/ec3/04_VERIFICATION.md`.

No modificados: todo lo demás bajo `apps/ec3/` (ver sección 2), `apps/knowledge/`,
`.env.example`, `config/settings.py`, `config/urls.py`, los 3 hooks de
`apps.analytics` (sólo se corrigió `reporting.py`, que ellos importan sin
cambios en su propia firma).

## 6. Modelos y migraciones

Ningún modelo ni migración nueva en esta sesión — las 3 migraciones
(`0001_initial`, `0002_history_guards`, `0003_epdversion_retrieved_at_
alter_epdversion_snapshot`) son de Codex y no requirieron cambios.
`manage.py makemigrations --check --dry-run` confirma "No changes detected"
tras todos los cambios de esta sesión.

## 7. Endpoints internos (13 en total, prefijo `/api/integrations/ec3/`)

De Codex: `GET search/`, `GET epds/<id>/`, `POST epds/<id>/ingest/`, `GET,POST
candidates/`, `GET candidates/<id>/`, `POST candidates/<id>/review/`, `POST
candidates/<id>/promote/`, `POST candidates/<id>/mapping/`.

Nuevos esta sesión: `GET candidates/<id>/eligibility/`, `GET epds/<id>/
versions/`, `GET candidates/<id>/compare/`, `GET materials/<id>/
opportunities/`, `GET observability/`. Todos exigen sesión de superusuario
activo (`IsAuthenticated` + `require_reviewer`), igual que los de Codex;
`materials/<id>/opportunities/` añade además `require_tenant_permission`
(`MATERIAL_MAPPING_VIEW`) por defensa en profundidad.

## 8. Endpoints EC3 usados (contrato oficial, sin invención)

`GET /v2/epds/search` (búsqueda), `GET /epds/{openXpdUuid}` (detalle) —
ambos documentados en `docs/integrations/ec3/02_OFFICIAL_CONTRACT.json`
(hash-pinned). Ningún endpoint EC3 nuevo se invocó esta sesión; toda la
verificación fue offline con fixtures sintéticos.

## 9. Resultados de pruebas

Suite EC3 completa tras esta sesión: **63/63 OK** (~68 s) — 36 de gobernanza/
cliente/rate-limit (Codex, sin cambios), 17 de comparabilidad/oportunidad
(nuevo), 5 del comando de refresh (nuevo), 4 de observabilidad (nuevo), 1 de
reutilización cruzada de fuentes (nuevo). Suite MATERIAL-INTELLIGENCE
relevante (`test_material_comparable_sets`, `test_material_opportunities`,
`test_material_hotspots`, `test_material_environmental_comparison`,
`test_material_intelligence_e2e`, `test_material_intelligence_security_audit`):
**51/51 OK**, sin regresión. `manage.py check`: sin incidencias.
`makemigrations --check --dry-run`: sin cambios. `git diff --check`: correcto.
Regresión final SOURCE-WATCH-01 (analytics+knowledge+iot, previa e
independiente de esta macrofase): 1395 tests, 27 errores — baseline
preexistente y documentado, cero relación con EC3.

## 10. Seguridad

Verificado de nuevo esta sesión: `.env.example` sin secretos (`EC3_API_TOKEN=`
vacío), `.env` real del entorno sin ninguna entrada `EC3_*` (token realmente
ausente, no sólo vacío por convención), token nunca en logs (`@sensitive_
variables` en `client.py`), token nunca expuesto al frontend (todo acceso
pasa por el backend), `require_reviewer`/`IsAuthenticated` en cada endpoint,
tenant isolation vía `require_tenant_permission` donde corresponde, timeouts
(5/20 s), límite de payload (2 MiB), validación estricta de todo dato
externo antes de persistir, errores seguros (nunca se devuelve el cuerpo
upstream ni una traza interna).

## 11. Provenance y versionado

`provenance()` expone fuente, external ID, EPD, versión upstream/local,
fecha de recuperación, unidad declarada, lifecycle scope, checksum y
metadata de calidad — sin cambios esta sesión. El ledger existente recibe
`external_source`/`ec3_candidate_id`/`ec3_review_id` vía `ec3.reporting.
ledger_source`, sin cambios. Historia nunca se reescribe: `Immutable`/
`ImmutableQuerySet` más guards SQL por trigger en migración `0002`.

## 12. Supuestos de licenciamiento

Sin cambios respecto a lo ya documentado por Codex: `EC3_STORAGE_ALLOWED`
requiere `EC3_RIGHTS_REFERENCE` y `EC3_RIGHTS_VALID_UNTIL` explícitos y
vigentes; sin eso, ingestión bloqueada (`require_storage`) y search/detail
funcionan sin cache. Nunca se asume un derecho de almacenamiento comercial
implícito por tener la cuenta Pilot habilitada.

## 13. Bloqueos externos

**Único bloqueo**: `EC3_API_TOKEN` no está disponible en este entorno
(confirmado explícitamente esta sesión: sin entrada `EC3_*` en el `.env`
real). Es una credencial que sólo Building Transparency puede emitir para
esta cuenta Pilot — no es competencia de esta sesión resolverlo. Todo lo
demás de la misión se completó offline.

## 14. Variables de entorno requeridas para el smoke real

`EC3_ENABLED=true`, `EC3_API_TOKEN=<bearer real de la cuenta Pilot>`,
`EC3_STORAGE_ALLOWED=true` (sólo si el acuerdo real lo permite),
`EC3_RIGHTS_REFERENCE=<referencia interna del acuerdo>`,
`EC3_RIGHTS_VALID_UNTIL=<fecha ISO>`, `EC3_CACHE_TTL_SECONDS` y
`EC3_EVIDENCE_MAX_AGE_HOURS` (opcionales, tienen default seguro).

## 15. Procedimiento exacto de smoke real (cuando exista el token)

Ver [docs/integrations/ec3/04_VERIFICATION.md](integrations/ec3/04_VERIFICATION.md#bloqueo-externo-exacto-y-siguiente-paso)
— 6 pasos: activar config y verificar `manage.py check`/migraciones; una
página de búsqueda real con oMF documentado (acero estructural preferido);
inspeccionar un detalle real sin confirmar aplicabilidad; si los derechos lo
permiten, ingerir ese ID y completar el flujo humano de
`03_OPERATIONS.md`; registrar el resultado real; opcionalmente verificar
`eligibility/`, `observability/` y `compare/` sin que ninguno ingiera,
promueva o apruebe nada por sí mismo.

## 16. Rollback

Ver [docs/integrations/ec3/03_OPERATIONS.md#rollback](integrations/ec3/03_OPERATIONS.md#rollback):
`EC3_ENABLED=false` para desactivación inmediata sin pérdida de historial;
`revoke_material_mapping` (ya existente) para retirar un mapping específico;
`purge_ec3_cache --all` para el cache; reversión de migraciones sólo
documentada, no probada, y explícitamente destructiva si se ejecuta.

## 17. Deuda técnica real restante

- El smoke real (capability 15) — el único ítem bloqueado externamente.
- La previsualización de oportunidad EC3 (`opportunity.py`) sólo considera
  candidatos ya propuestos por un humano; no hay (ni debe haberlo sin
  gobernanza adicional) un descubrimiento automático de candidatos EC3 para
  un hotspot detectado — es una decisión de diseño deliberada, no un
  descuido, pero vale la pena que quede explícito para quien continúe.
- `01_ARCHITECTURE_DISCOVERY.md` y `02_OFFICIAL_CONTRACT.json` no se
  revisaron esta sesión (no había necesidad: ninguna capacidad nueva tocó
  el contrato upstream en sí).
- La reversión de migraciones EC3 (`0001`-`0003`) permanece documentada pero
  nunca ejecutada ni probada en este entorno.

## 18. Verdict final

**IMPLEMENTATION COMPLETE — REAL API VALIDATION PENDING.**

Las 16 áreas de capacidad de la misión están completas, probadas y
documentadas offline. El único elemento pendiente es la validación con la
API real de EC3/openEPD, bloqueada exclusivamente por la ausencia de
`EC3_API_TOKEN` en este entorno — una credencial externa que sólo Building
Transparency puede emitir. No se realizó commit ni push, conforme a la
instrucción explícita de esta macrofase.
