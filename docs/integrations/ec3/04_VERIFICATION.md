# EC3-01 — Auditoría y verificación

Estado: implementación completa y validada, incluido el smoke real contra la
cuenta Pilot (2026-09-12). Verdict: **DONE**. Ver
[EC3-01-FINAL-REPORT.md](../../EC3-01-FINAL-REPORT.md) sección 15 para el
detalle completo del smoke real; este documento conserva el registro
histórico de la fase offline y añade el resultado real al final.

## Auditoría y cierre de brechas (sesión posterior)

Una sesión posterior auditó el trabajo descrito en este documento (de una sesión
"Codex" concurrente) contra la misión EC3 completa y encontró la implementación
sólida y correctamente gobernada, sin necesidad de rehacer nada. Cerró las brechas
reales que quedaban:

- **Comparabilidad EC3 (capability 7)** — nueva `apps/ec3/comparability.py`:
  comparación determinista y explicable entre dos EPDs EC3 ya ingeridas.
- **Motor de oportunidad potencial (capability 8)** — nueva
  `apps/ec3/opportunity.py`, en dos capas: reutilización directa del motor
  MATERIAL-INTELLIGENCE ya existente para materiales EC3 ya mapeados/activos, y una
  previsualización EC3-específica para candidatos ya propuestos pero aún no
  aplicados. Ver detalle completo en
  [03_OPERATIONS.md](03_OPERATIONS.md#comparabilidad-y-oportunidad-potencial).
- **Corrección de una brecha real de reutilización**: `ec3.reporting.factor_quality`
  nunca poblaba `known["standard"]` (generación EN 15804), lo que excluía
  permanentemente a cualquier material mapeado a EC3 del motor de conjuntos
  comparables existente (`standard_unknown` siempre). Corregido derivando ese campo
  del `compliance` real de la EPD, nunca inventado. Probado en
  `CrossSourceReuseTests` (EC3 vs ÖKOBAUDAT, mismo motor, sin bifurcación).
- **API interna (capability 9)**: se añadieron los endpoints que faltaban —
  `eligibility/`, `epds/<id>/versions/`, `candidates/<id>/compare/`,
  `materials/<id>/opportunities/`, `observability/`.
- **Refresh/jobs (capability 10)**: nuevo comando `refresh_known_ec3_epds`
  (re-valida EPDs ya conocidas, nunca descubre nuevas, continue-on-error,
  respeta el presupuesto de 100 tokens/min).
- **Observabilidad (capability 13)**: nuevo `apps/ec3/observability.py`, derivado
  enteramente de estado ya persistido (sin modelo de métricas nuevo); se afinó
  `services.ingest_epd` para distinguir `ec3_rate_limited` de otros fallos en
  `SyncRun.message`.
- Ninguna de estas adiciones creó un modelo de persistencia nuevo, un motor
  paralelo o una fuente de verdad duplicada; todas reutilizan `evaluate_version`,
  `select_material_factor`, `unit_conversion.convert_value` y el `SyncRun`/
  `EnvironmentalSource` de Knowledge Hub ya existentes.
- **Corrección adicional tras el smoke real** (ver más abajo):
  `apps/ec3/schemas.py::project_epd` rechazaba EPDs reales cuyo objeto `ec3`
  trajera `batch_specific`/`manufacturer_specific`/`plant_specific`/
  `product_specific` con valor `null` — la cuenta real lo devuelve así
  legítimamente. Corregido para aceptar `None` en esos 4 flags.

## Entorno aislado

Python 3.13, Django 6.0.4, DRF 3.17.1, PostgreSQL 18 local en loopback:55443.
Clúster exclusivo `.tmp-pg-ec3`; bases descartables `test_ec3test` y
`test_ec3knowledge`. No se migraron bases de producción ni el clúster de la sesión
SOURCE-WATCH. No se descargaron EPDs reales ni se hicieron llamadas autenticadas.

## Evidencia de pruebas

| Gate | Resultado |
|---|---|
| Suite EC3 inicial (sesión Codex) | 33/33 OK, 18.784 s |
| Regresión ambiental amplia (sesión Codex) | 305/305 OK, 421.423 s |
| Gate de versionado ampliado + selector + E2E existente (sesión Codex) | 53/53 OK, 85.455 s |
| **Suite EC3 completa tras el cierre de brechas + smoke real (sesión posterior)** | **64/64 OK, ~58 s** (37 gobernanza/cliente/rate-limit incl. regresión del fix de schema + 17 comparabilidad/oportunidad + 5 refresh command + 4 observabilidad + 1 cross-source reuse) |
| MI-01D/MI-01H (`test_material_comparable_sets`, `test_material_opportunities`, `test_material_hotspots`, `test_material_environmental_comparison`, `test_material_intelligence_e2e`, `test_material_intelligence_security_audit`) tras los cambios EC3 | 51/51 OK, sin regresión |
| `manage.py check` (con `apps.ec3` incluida) | Sin incidencias |
| `makemigrations --check --dry-run` | Sin cambios pendientes |
| Regresión final SOURCE-WATCH-01 (analytics+knowledge+iot, previa a esta fase) | 1395/1395, 27 errores — baseline preexistente documentado, cero nuevas fallas |
| `git diff --check` | Correcto |

Los conteos de la sesión Codex y de la sesión posterior corresponden a ejecuciones
distintas sobre bases de datos distintas; no se suman entre sí como una única prueba.

Los conteos de distintas ejecuciones se superponen; no sumarlos como pruebas únicas.
Logs locales, ignorados por Git: `.tmp-pg-ec3/ec3-tests.log`,
`regression-analytics.log`, `final-ec3-tests.log`, `final-gates.log`,
`regression-knowledge.log`.

La primera ejecución descubrió y corrigió un bloqueo PostgreSQL sobre el lado
nullable de un JOIN en la propuesta de mapping y la forma de errores de entrada
DRF. Las pruebas del limiter limpian únicamente su propia tabla: el flush global
heredado del repositorio no contempla algunas FKs de tablas legacy unmanaged.
No se alteraron esas tablas ni los tests heredados. Todos los errores de esa
primera ejecución se resolvieron y la misma suite pasó después.

## E2E de acero y límites de la evidencia

`apps.ec3.tests.test_governance.GovernanceTests.test_steel_e2e_work_activity_search_epd_mapping_eligible_calculation_provenance`
crea obra, actividad, material y recepción de 1.000 kg. Usa **respuestas sintéticas**
con contrato openEPD verificado: búsqueda → detalle → knowledge → candidato →
revisión humana explícita → factor borrador → transiciones existentes → mapping
propuesto/aprobado → selector/elegibilidad → cálculo real del motor.

Resultado del caso sintético: **1.800 kgCO2e**, proveniente de GWP A1-A3 de 1.800
kgCO2e por 1.000 kg declarados, método EF 3.0. Esto no representa un producto ni
un factor real de Building Transparency. El ID `ec3test1`, las organizaciones,
la EPD y los links `example.org` son exclusivamente fixtures.

El caso comprueba fuente, external ID, EPD, versiones upstream/local, fecha de
recuperación, unidad declarada, lifecycle scope, checksum y metadata de calidad.
Después de cambiar la EPD, el selector bloquea nuevos usos y conserva el cálculo
anterior. El ledger vuelve a exponer su provenance congelada. Otra prueba cubre
A → B → A para impedir que la aprobación de A vuelva a activarse por coincidencia
de checksum. Hay pruebas de historia inmutable en ORM y SQL, presupuesto compartido
con conexiones concurrentes, aislamiento de permisos, 429, retry/backoff,
timeouts, 5xx, no redirects, límites de bytes y ausencia de cache sin derechos.

## Alcance de cambios

- App modular `backend/apps/ec3/`, con migraciones propias 0001–0003.
- Registro en `backend/config/settings.py` y URL raíz en `backend/config/urls.py`.
- Guard EC3 en `material_factor_selector.py`.
- Adaptadores de lectura en `material_quality.py` y `material_ledger.py`.
- Variables sin valores secretos en `.env.example`.
- Documentos de descubrimiento, contrato oficial, operación y este reporte.

Añadido por la sesión posterior (sin tocar nada de lo anterior salvo lo indicado):

- Nuevo `apps/ec3/comparability.py`, `apps/ec3/opportunity.py`,
  `apps/ec3/observability.py`.
- Nuevo comando `apps/ec3/management/commands/refresh_known_ec3_epds.py`.
- `apps/ec3/views.py`/`urls.py`: 5 endpoints nuevos (ver 03_OPERATIONS.md).
- `apps/ec3/services.py`: `ingest_epd` distingue `ec3_rate_limited` en
  `SyncRun.message` (antes cualquier `RateLimited` se perdía como
  `ec3_ingestion_failed` genérico).
- `apps/ec3/reporting.py`: `factor_quality` ahora deriva `known["standard"]` del
  `compliance` real de la EPD — corrige la exclusión permanente de todo material
  mapeado a EC3 del motor de conjuntos comparables de MATERIAL-INTELLIGENCE.
- `apps/ec3/schemas.py`: `project_epd` acepta `null` real en los 4 flags de
  especificidad EC3 (nunca en `category`) — encontrado por el smoke real
  (ver sección "Smoke real ejecutado" más abajo).
- Nuevos tests: `test_comparability_opportunity.py` (17), `test_refresh_command.py`
  (5), `test_observability.py` (4), `test_client.py` +1 (regresión del fix de schema).
- Migraciones EC3 aplicadas a la base real `material01d` (nunca lo habían sido;
  sólo existían en la base de test efímera) — sin migraciones nuevas creadas
  (ningún modelo nuevo). Sin cambios en `apps/knowledge/` ni en documentación
  SOURCE-WATCH.

No se editaron archivos de `backend/apps/knowledge/` ni documentación SOURCE-WATCH.
Sus modificaciones concurrentes permanecen en el working tree. La integración
usa sus modelos y registro de conectores mediante interfaces existentes. No hay
ediciones frontend, motor completo de recomendaciones, commit, push ni despliegue.

## Repetición local

Con el clúster aislado en marcha, desde la raíz, PowerShell:

```powershell
$env:DATABASE_ENGINE = 'django.db.backends.postgresql'
$env:DATABASE_HOST = '127.0.0.1'
$env:DATABASE_PORT = '55443'
$env:DATABASE_USER = 'ec3test'
$env:DATABASE_PASSWORD = 'local-trust'
$env:DATABASE_NAME = 'ec3test'
$ec3Python = '.tmp-pg-material01b/venv/Scripts/python.exe'
& $ec3Python backend/manage.py test apps.ec3.tests --noinput --keepdb
& $ec3Python backend/manage.py test apps.analytics.test_material_factor_selector apps.analytics.test_material_data_e2e apps.analytics.test_material_quality apps.analytics.test_material_ledger --noinput --keepdb
& $ec3Python backend/manage.py check
& $ec3Python backend/manage.py makemigrations --check --dry-run
git diff --check
```

La suite completa Knowledge debe ejecutarse en una base descartable independiente:
algunos tests heredados de concurrencia truncan tablas, incluido el historial de
migraciones. No reutilizar esa base con `--keepdb` en ejecuciones posteriores sin
recrearla. Esta fase no modifica ese comportamiento heredado.

## Bloqueo externo (histórico — resuelto)

Al momento de escribir las secciones anteriores, la comprobación de
configuración imprimía sólo booleanos y confirmaba: `EC3_API_TOKEN_present=
False`, `EC3_ENABLED=False`, `EC3_STORAGE_ALLOWED=False`. El bloqueo (falta
de `EC3_API_TOKEN`) fue resuelto por el usuario, quien confirmó el token
disponible en `backend/.env` (gitignorado). El procedimiento de 6 pasos que
seguía en esta sección fue ejecutado real y completo — ver
[EC3-01-FINAL-REPORT.md](../../EC3-01-FINAL-REPORT.md) sección 15 para el
detalle paso a paso y los resultados reales. Se conserva este historial para
que quede explícito qué se sabía antes del smoke real y qué cambió después.

## Smoke real ejecutado (2026-09-12) — resumen

Autenticación real confirmada sin exponer el token; búsqueda real (la
categoría `"StructuralSteel"` preferida por la misión fue rechazada por la
API real — `Unknown EC3 Material Filter field accessible_categories`; se usó
la categoría del ejemplo oficial `AluminiumBillets` en su lugar, sin
inventar ningún nombre de categoría no documentado); detalle real de
`ec33srzz`; validación de schema que **encontró y corrigió** un mismatch
real (`ec3.batch_specific` puede ser `null` en datos reales, no sólo
booleano); ingesta controlada única con `EpdVersion` real persistido;
provenance/checksum reales verificados; rate limiter compartido confirmado
rastreando consumo real (3 eventos tras 3 solicitudes, muy por debajo del
cupo de 100/min). Detalle completo, incluidas las migraciones EC3 que
faltaban aplicar a la base real y se aplicaron en el proceso, en
[EC3-01-FINAL-REPORT.md](../../EC3-01-FINAL-REPORT.md).

## Verdict

**DONE.** Todo lo definido en la misión EC3 está implementado, probado
offline y ahora también validado con datos reales de la cuenta Pilot real.
