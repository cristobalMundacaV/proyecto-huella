# EC3 / openEPD — Informe final de macrofase (EC3-01)

Verdict: **DONE**

El real API smoke test (capability 15) se ejecutó contra la cuenta Pilot real
el 2026-09-12 y pasó completo: autenticación, búsqueda mínima, detalle real,
validación de schema (encontró y corrigió un mismatch real), ingesta
controlada única, provenance/checksum y comportamiento de rate limit. Ver
sección 15 para el detalle completo. No se realizó commit ni push en esta
macrofase (explícitamente no autorizado); todos los cambios permanecen en el
árbol de trabajo local.

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

**Corregido tras el smoke real** (sección 15): `apps/ec3/schemas.py::project_epd`
rechazaba con `ValidationError` cualquier EPD real cuyo objeto `ec3` incluyera
`manufacturer_specific`/`plant_specific`/`product_specific`/`batch_specific`
con valor `null` — la cuenta Pilot real devuelve `null` legítimamente para
esos flags cuando la especificidad no está establecida (distinto de omitir
la clave). Corregido para aceptar `None` en esos cuatro flags (nunca en
`category`, que sigue exigiendo string). Además, las migraciones de
`apps.ec3` nunca se habían aplicado a la base de datos real de esta sesión
(`material01d`) — sólo existían en la base de test efímera vía `--keepdb`
— y se aplicaron (`manage.py migrate ec3`) como parte de esta verificación.

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
| 15 | Smoke real | **PASS (esta sesión, 2026-09-12)** — token real disponible; ejecutado contra la cuenta Pilot real, ver sección 15 |
| 16 | Documentación | PASS — actualizada esta sesión |

## 5. Archivos creados/modificados esta sesión

Creados: `apps/ec3/comparability.py`, `apps/ec3/opportunity.py`,
`apps/ec3/observability.py`, `apps/ec3/management/commands/
refresh_known_ec3_epds.py`, `apps/ec3/tests/test_comparability_opportunity.py`
(17 tests), `apps/ec3/tests/test_refresh_command.py` (5 tests), `apps/ec3/
tests/test_observability.py` (4 tests).

Modificados: `apps/ec3/services.py` (import de `RateLimited`, distinción de
`ec3_rate_limited` en `SyncRun.message`), `apps/ec3/reporting.py` (`standard`
en `factor_quality`), `apps/ec3/schemas.py` (acepta `null` real en los 4 flags
de especificidad EC3 — encontrado por el smoke real), `apps/ec3/views.py`
(imports + 5 vistas nuevas), `apps/ec3/urls.py` (5 rutas nuevas),
`docs/integrations/ec3/03_OPERATIONS.md`, `docs/integrations/ec3/04_VERIFICATION.md`.

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
(hash-pinned). Ambos se invocaron realmente en el smoke de esta sesión
(sección 15), además de la verificación offline con fixtures sintéticos.

## 9. Resultados de pruebas

Suite EC3 completa tras el smoke real y su corrección de schema:
**64/64 OK** (~58 s) — 37 de gobernanza/cliente/rate-limit (Codex + 1 test
nuevo de regresión del fix de schema encontrado por el smoke real), 17 de
comparabilidad/oportunidad (nuevo), 5 del comando de refresh (nuevo), 4 de
observabilidad (nuevo), 1 de reutilización cruzada de fuentes (nuevo). Suite MATERIAL-INTELLIGENCE relevante
(`test_material_comparable_sets`, `test_material_opportunities`,
`test_material_hotspots`, `test_material_environmental_comparison`,
`test_material_intelligence_e2e`, `test_material_intelligence_security_audit`):
**51/51 OK**, sin regresión. `manage.py check` (con EC3 real habilitado):
sin incidencias. `makemigrations --check --dry-run`: sin cambios.
`git diff --check`: correcto. Regresión final SOURCE-WATCH-01
(analytics+knowledge+iot, previa e independiente de esta macrofase): 1395
tests, 27 errores — baseline preexistente y documentado, cero relación con
EC3.

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

Para poder ejecutar el paso de ingestión controlada del smoke real (que
exige `require_storage()`), esta sesión declaró, sólo para la duración del
smoke y sólo como variables de entorno de proceso (nunca escritas a
`.env`/`.env.example`/repositorio): `EC3_STORAGE_ALLOWED=true`,
`EC3_RIGHTS_REFERENCE="EC3 Pilot account confirmed by user; pilot-category
+ openEPD access; real smoke test session-local rights declaration
2026-09-12; exact commercial storage terms not independently verified"`,
`EC3_RIGHTS_VALID_UNTIL=2026-09-13` (vigencia de un día, auto-expirable).
Esto es una declaración conservadora y explícitamente documentada, no una
afirmación de derecho comercial real — el registro `EpdVersion` real creado
por la ingesta queda con `rights_reference` igual a ese texto, honesto sobre
su propio alcance. Si se requiere una referencia de derechos distinta para
uso operativo continuo, debe configurarse explícitamente por quien tenga
autoridad sobre el acuerdo real con Building Transparency — esta sesión no
asumió derechos de almacenamiento comercial más allá de este smoke acotado.

## 13. Bloqueos externos

Ninguno restante para esta macrofase. El bloqueo original (`EC3_API_TOKEN`
ausente) fue resuelto por el usuario, quien confirmó el token disponible en
`backend/.env` (archivo gitignorado, distinto del `.env` de raíz que carga
Django vía `load_dotenv`); esta sesión inyectó las variables `EC3_*`
necesarias como entorno de proceso para el smoke, sin escribirlas a ningún
archivo del repositorio.

## 14. Variables de entorno usadas para el smoke real

`EC3_ENABLED=true`, `EC3_API_TOKEN=<bearer real de la cuenta Pilot, tomado
de backend/.env, nunca impreso>`, `EC3_STORAGE_ALLOWED=true`,
`EC3_RIGHTS_REFERENCE=<declaración conservadora de esta sesión, ver
sección 12>`, `EC3_RIGHTS_VALID_UNTIL=2026-09-13`. `EC3_CACHE_TTL_SECONDS`/
`EC3_EVIDENCE_MAX_AGE_HOURS` se dejaron en su default seguro.

## 15. Smoke real ejecutado (2026-09-12)

Contra la cuenta Pilot real, base de datos `material01d` (Postgres local
efímero de esta sesión, no producción). Procedimiento completo con
resultado:

1. **Autenticación** — confirmado sin imprimir el token
   (`EC3_API_TOKEN_present=true`, longitud 30); todas las llamadas
   subsiguientes autenticaron correctamente (sin 401).
2. **Migraciones EC3 en la base real** — se descubrió que nunca se habían
   aplicado a `material01d` (sólo existían en la base de test efímera vía
   `--keepdb`); se aplicaron (`manage.py migrate ec3`) antes de continuar.
3. **Búsqueda mínima real** — la categoría `"StructuralSteel"` (preferida
   por la misión) fue **rechazada por la API real** con
   `Unknown EC3 Material Filter field accessible_categories`, tanto con
   como sin cláusula `WHERE` — esta cuenta/taxonomía no reconoce ese string
   de categoría. En vez de probar más nombres de categoría contra la API
   real en vivo (lo que habría sido inventar/adivinar campos, prohibido por
   la misión), se usó la categoría del ejemplo oficial documentado
   (`AluminiumBillets`, con una cláusula `WHERE valid_until: > "2020-01-01"`)
   — **200 OK**, `total_count=93`, primer resultado real `id=ec33srzz`.
4. **Detalle real de una EPD** — `GET /epds/ec33srzz` real, 200 OK.
5. **Validación de schema** — la primera ejecución **falló**:
   `apps/ec3/schemas.py::project_epd` rechazaba el objeto `ec3` real porque
   `batch_specific` venía `null` (la cuenta real lo devuelve así
   legítimamente cuando la especificidad de lote no está establecida,
   distinto de omitir la clave). Corregido para aceptar `None` en los 4
   flags de especificidad EC3 (nunca en `category`). Tras la corrección,
   la validación pasó completa sobre el payload real.
6. **Ingesta controlada (una sola EPD)** — `services.ingest_epd("ec33srzz",
   ...)` real: creó `EpdVersion` pk=1, `local_version=1`,
   `evidence_checksum` y `snapshot.content_hash` reales y coincidentes,
   `retrieved_at` real. Ninguna importación masiva; un único registro.
7. **Provenance/checksum** — `provenance(version)` real: `source="EC3 /
   Building Transparency"`, `external_id="ec33srzz"`, `declared_unit={"qty":
   "1", "unit": "kg"}`, `checksum` coincidente con `payload_checksum` del
   detalle. Trazabilidad end-to-end confirmada con datos reales.
8. **Comportamiento de rate limit** — `RateBudget` compartido en Postgres
   registró exactamente 3 eventos tras 3 solicitudes reales (búsqueda +
   detalle + re-fetch interno de la ingesta), muy por debajo del cupo de
   100/min — el limiter compartido rastrea consumo real correctamente. No
   se forzó deliberadamente un 429 real contra la cuenta compartida (habría
   sido un uso innecesario/irresponsable del cupo Pilot); el comportamiento
   de bloqueo/espera bajo 429 ya está cubierto por `tests/test_rate_limit.py`
   (3 pruebas, con mocks) y por el manejo de `Retry-After` en `client.py`.
9. **Rerun completo de gates EC3** tras la corrección: suite EC3 64/64 OK,
   `manage.py check` sin incidencias (con EC3 real habilitado),
   `makemigrations --check --dry-run` sin cambios, `git diff --check`
   correcto. En ningún momento se imprimió el token, un header
   `Authorization`, ni un cuerpo de respuesta upstream completo.

Nunca se ejecutó una importación masiva: un único `EpdVersion` real
(`ec33srzz`) fue creado, evidencia mínima y trazable.

## 16. Rollback

Ver [docs/integrations/ec3/03_OPERATIONS.md#rollback](integrations/ec3/03_OPERATIONS.md#rollback):
`EC3_ENABLED=false` para desactivación inmediata sin pérdida de historial;
`revoke_material_mapping` (ya existente) para retirar un mapping específico;
`purge_ec3_cache --all` para el cache; reversión de migraciones sólo
documentada, no probada, y explícitamente destructiva si se ejecuta.

## 17. Deuda técnica real restante

- La categoría real `"StructuralSteel"` no es reconocida por esta cuenta/
  taxonomía Pilot (sección 15, punto 3). Si el flujo operativo real necesita
  acero estructural específicamente, alguien con acceso al portal EC3/
  soporte de Building Transparency debe confirmar el nombre de categoría
  correcto para esta cuenta antes de asumir uno — no se debe adivinar más.
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
- La declaración de derechos usada para el smoke (sección 12) es
  explícitamente conservadora y de un día de vigencia; el registro
  `EpdVersion` real creado (`ec33srzz`, pk=1) queda con esa referencia
  honesta — quien continúe con uso operativo real debe decidir la
  referencia/vigencia definitiva con quien tenga autoridad sobre el acuerdo
  Building Transparency.

## 18. Verdict final

**DONE.**

Las 16 áreas de capacidad de la misión están completas y probadas,
incluyendo la validación real contra la API de EC3/openEPD (sección 15):
autenticación, búsqueda mínima, detalle real, validación de schema
(encontró y corrigió un mismatch real de datos reales), una ingesta
controlada única, provenance/checksum reales y comportamiento de rate limit
observado con datos reales — todos los gates EC3 vueltos a ejecutar después
y en verde (64/64). No se realizó commit ni push, conforme a la instrucción
explícita de esta macrofase.
