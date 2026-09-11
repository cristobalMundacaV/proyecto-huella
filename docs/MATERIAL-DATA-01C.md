# MATERIAL-DATA-01C — Governed Material Factor Candidates

## Auditoría inicial

El working tree estaba limpio en `73195f0`; el historial local ya incluía 01B en
`b6e558b`. Esto difiere del estado sin commit descrito en la solicitud. No se
revirtió ni reconstruyó 01B, no se modificaron datos de producción, y no se hizo
commit, push o deploy. Se revisaron sus modelos, hidratación, snapshots, parser,
fixtures, migraciones y pruebas, además de los modelos y servicios de candidatos,
reconciliación, gobernanza de factores, unidades y permisos de HuellaChile.

`EnvironmentalFactorCandidate` sigue vinculado exclusivamente a
`HuellaChileEmissionFactorFact`. Su reconciliación, mapping, equivalencia y APIs
no se modifican. No hay GenericForeignKey, matching, equivalencia funcional,
activación automática ni conexión con MaterialOperacional o sus cálculos.

## Implementación y archivos

Todos los archivos de aplicación están bajo `backend/apps/analytics/`:

| Archivo | Responsabilidad |
|---|---|
| `models/material_candidates.py` | MaterialEnvironmentalFactorCandidate, MaterialFactorCandidateReview, protección ORM de evidencia y origen |
| `models/__init__.py` | Exportación de los dos modelos |
| `services/material_candidates.py` | Eligibility, canonicalización, normalización, build, policy de superusuario, revisión y promoción |
| `views_material_candidates.py`, `urls.py` | API global gobernada, filtros y paginación |
| `management/commands/build_okobaudat_material_factor_candidates.py` | Construcción incremental e idempotente; nunca promueve |
| `migrations/0065_material_factor_candidates.py` | Modelos, relaciones PROTECT/OneToOne y CHECK constraints |
| `migrations/0066_material_candidate_history_guards.py` | Triggers PostgreSQL de historia, revisión, identidad y promoción a borrador |
| `test_material_candidates.py` | Contratos numéricos, gobernanza, API y concurrencia real |
| `test_model_modularization.py` | Sustituye un conteo histórico obsoleto por la identidad entre registro y API pública de modelos |

Se agregan también `scripts/smoke_material_data_01c.py`, este informe y
[`material-data-01c-smoke.json`](material-data-01c-smoke.json).
Las migraciones dependen de analytics 0064 y knowledge 0013. No convierten datos
existentes ni modifican los facts de 01A/01B.

## Contrato y gobernanza

- Un candidato por perfil histórico; indicador elegido mediante identidad exacta.
  A2 exige `GWP-total`, A1 exige `GWP`; nunca se suman subcategorías. Las tres
  subcategorías A2 quedan en provenance con valores y UUIDs originales.
- Normalización: GWP explícito A1-A3 / cantidad declarada positiva, Decimal de
  precisión 80. Canonicalización reutiliza el servicio de unidades existente.
  El grupo de unidad de resultado debe ser el UUID oficial verificado y una
  etiqueta admitida por el contrato; unidades ambiguas fallan cerradas.
- Se conservan valor/unidad raw, identidad y versión de indicador/unidad,
  cantidad/unidad declaradas, normalización, estándar, límite A1-A3, perfil,
  snapshot/hash/fecha/URL, referencias y términos originales. Se verifican bytes
  y hashes de snapshots de detalle y referencias sin descargar upstream.
- `detected` significa inelegible al construir; `requires_review`, compatibilidad
  mecánica sin revisión; `ready_for_review`, aprobación humana explícita para
  promoción; `rejected`, rechazo; `promoted_to_draft`, promoción completada.
  Cada nueva revisión agrega un registro inmutable. Rechazo/reaprobación conserva
  todas las decisiones. La promoción congela candidato y revisiones.
- Policy tanto en API como en servicios: sólo superusuario activo puede consultar
  o gobernar candidatos globales, siguiendo el perímetro global de HuellaChile.
  Un administrador de tenant no obtiene acceso; no se acepta tenant ni factor
  objetivo en la promoción. POST separados; no PATCH de transiciones.
- Build bloquea el perfil; review/promotion bloquean el candidato y el estado de
  fuente, coordinándose con el inicio de sincronización existente. Promoción
  atómica; repetir devuelve error de validación (HTTP 400), nunca duplica.
- Cada promoción crea un FactorAmbiental global separado, categoría
  `materiales_a1a3`, y VersionFactorAmbiental `borrador`. Ambos contextos llevan
  `source_candidate_id`, revisión, estándar y provenance. Las relaciones inversas
  `material_source_candidate` permiten volver al candidato desde ambos modelos.
- Vigencia: fuente habilitada, catálogo publicado con el snapshot correspondiente,
  sin versión posterior activa del mismo UUID/datastock. Sincronización en curso,
  publicación parcial, fuente retirada o historial bloquean aprobación/promoción.
  La API recalcula esta condición; no confunde eligibility inicial con vigencia
  actual. No interpreta edad del snapshot como vigencia legal de la EPD.
- Contexto funcional conserva clasificación, tipo, ubicación, owner upstream,
  descripción y cumplimiento. Propiedades técnicas, equivalencia e intended use
  ausentes quedan `unknown`; comparación queda `requires_review`. La revisión
  admite sólo `intended_use` y `mapping_note` textuales como contexto humano
  separado; no admite IDs de materiales ni equivalencia automática.

## API

Prefijo: `/api/environmental-governance/material-factor-candidates/`.

| Método/ruta | Contrato |
|---|---|
| GET colección | Paginación 50, máximo 200 |
| GET `<id>/` | Evidencia, normalización, revisiones, promoción y eligibility actual |
| GET `<id>/eligibility/` o `<id>/compatibility/` | Evaluación mecánica determinista; no equivalencia funcional |
| POST `<id>/review/` | `{"decision":"approved","note":"Revisión técnica","context":{"intended_use":"..."}}`; también `rejected` |
| POST `<id>/promote/` | Objeto vacío; respuesta 201 con factor_id, version_id y estado `borrador` |

Filtros exactos: `status`, `standard`, `uuid`/`process_uuid`,
`version`/`dataset_version`, `classification` (nombre de árbol, ID o etiqueta de
nodo), `location` (valor upstream), `input_unit`. No substring/fuzzy matching.

## Smoke oficial, sin red

El smoke usa los XML oficiales incluidos por 01B y registros de publicación de
catálogo sintéticos explícitos en una base PostgreSQL local aislada. Las
revisiones/promociones se ejecutan realmente, pero toda la transacción se revierte.
Los IDs del JSON son evidencia de esa ejecución efímera, no registros productivos.

| Estándar | UUID / versión | Cantidad | GWP raw | Factor candidato | Valor versión borrador |
|---|---|---|---|---|---|
| A2 | c54c16f6-4295-4749-bff0-ba7ed4bc9117 / 00.01.000 | 1000 kg | 847.351015163189 | 0.847351015163189 kgCO2e/kg | 0.8473510152 |
| A1 | f63ac879-fa7d-4f91-813e-e816cbdf1927 / 00.00.025 | 1 m3 | -647.4201396839651 | -647.4201396839651 kgCO2e/m3 | -647.4201396840 |

**Precisión del motor:** el DecimalField existente tiene 20 dígitos, 10 decimales.
La promoción usa ROUND_HALF_EVEN explícito y conserva por separado el valor
candidato y la regla en factor/version. El A1 persistido es `-647.4201396840`.
Valores fuera de rango o que se conviertan en cero por redondeo no son elegibles.
No se amplió el esquema numérico de HuellaChile ni se alteró el dato upstream.

## Validación local reproducible

- Suite inicial: **24/24 OK**, 87,260 s, PostgreSQL real (incluía una prueba de
  concurrencia de 01B importada por la primera versión de la suite).
- Regresión amplia: **443 pruebas**, 566,157 s; 442 pasaron. El único fallo fue
  el conteo fijo de 97 modelos de la prueba de modularización. Se verificaron
  **103 modelos iniciales y 105 finales**; se corrigió la prueba para comprobar
  identidad de los modelos públicos y ausencia de duplicados.
- Cierre sobre una base recreada con las migraciones finales: **139/139 OK**,
  102,213 s: **26 pruebas nuevas + 30 de detalle 01B + 83 de modularización**.
  Incluye concurrencia con conexiones independientes, UNIQUE/CHECK reales,
  rollback de promoción, triggers de inmutabilidad y permisos globales/tenant.
  No quedan fallos de pruebas pendientes; la prueba corregida también pasó
  individualmente. La regresión restante no se repitió sin necesidad.
- `manage.py check`: sin incidencias. `makemigrations --check --dry-run`: sin
  cambios pendientes. `git diff --check`: correcto.
- Migración 0066: desaplicación a 0065 y reaplicación verificadas en PostgreSQL;
  el smoke final se ejecutó después de reinstalar los triggers.
- Smoke A1/A2: dos candidatos, dos revisiones, dos promociones a borrador;
  repetición del builder con **0 creados, 2 existentes**. Escrituras revertidas.

Logs locales: `.tmp-pg-material01c/regression.log` y
`.tmp-pg-material01c/final-tests.log` (no versionados).

Desde la raíz, PowerShell. La ejecución realizada usa Python 3.13, Django 6.0.4 y
PostgreSQL 18.3 en un clúster aislado `.tmp-pg-material01c`, puerto 55440, usuario
local `material01c` (trust sólo loopback). El runner crea `test_material01c`.
El clúster creado para esta tarea quedó detenido al terminar; iniciarlo para repetir:

```powershell
& 'C:/Program Files/PostgreSQL/18/bin/pg_ctl.exe' -D "$PWD/.tmp-pg-material01c" -l "$PWD/.tmp-pg-material01c/server.log" -o '-h 127.0.0.1 -p 55440' start
$python = '.tmp-pg-material01b/venv/Scripts/python.exe'
$env:DATABASE_ENGINE = 'django.db.backends.postgresql'
$env:DATABASE_HOST = '127.0.0.1'
$env:DATABASE_PORT = '55440'
$env:DATABASE_USER = 'material01c'
$env:DATABASE_PASSWORD = 'local-trust'
$env:DATABASE_NAME = 'material01c'
& $python backend/manage.py test apps.knowledge apps.analytics.test_material_candidates apps.analytics.test_knowledge_v1 apps.analytics.test_factor_candidates apps.analytics.test_factor_reconciliation apps.analytics.test_materials_v2 apps.analytics.test_material_factor_governance apps.analytics.test_material_calculation_catalog apps.analytics.test_calculation_v2 apps.analytics.test_environmental_governance apps.analytics.test_methodology_governance_v1 apps.analytics.test_unit_conversion apps.analytics.test_rbac apps.analytics.test_rbac02_scope apps.analytics.test_tenant_configuration apps.analytics.test_model_modularization apps.analytics.test_fuel_factor_selector apps.analytics.test_energy_calculation_bootstrap apps.analytics.test_fuel_calculation_bootstrap --noinput
& $python backend/manage.py test apps.analytics.test_material_candidates apps.analytics.test_model_modularization apps.knowledge.test_okobaudat_detail --noinput --keepdb
& $python backend/manage.py check
& $python backend/manage.py makemigrations --check --dry-run
git diff --check
$env:DATABASE_NAME = 'test_material01c'
& $python backend/manage.py shell -c "exec(open('scripts/smoke_material_data_01c.py', encoding='utf-8').read())"
```

## Operación sugerida en producción — NO ejecutada

Con el entorno de aplicación ya configurado y 01B disponible, desde `backend/`:

```sh
python manage.py check
python manage.py migrate --plan
python manage.py migrate
python manage.py build_okobaudat_material_factor_candidates --process-uuid c54c16f6-4295-4749-bff0-ba7ed4bc9117 --dataset-version 00.01.000
python manage.py build_okobaudat_material_factor_candidates
```

El comando sólo lee perfiles ya hidratados y construye candidatos, incluidos
históricos inelegibles. Su resumen contiene profiles_seen, eligible, ineligible,
created, existing, a1, a2, missing_gwp, unsupported_unit y requires_review.
No hay promoción por comando ni cambios en datos operativos.

## Límites reales

La promoción conserva la precisión original como evidencia, pero el motor aplica
su precisión histórica de diez decimales. Unidades ajenas al catálogo seguro
existente requieren un contrato futuro. Cambiar el snapshot de catálogo sin
cambiar dataset version bloquea conservadoramente el perfil anterior; resolver
esa republicación requiere gobernanza de fuente, no una promoción forzada.
La consulta por clasificación recorre metadata JSON antes de paginar; un índice
específico puede ser necesario a mayor escala. SQLite tiene protecciones ORM,
pero los triggers y la garantía de concurrencia distribuida requieren PostgreSQL.

Algunas suites heredadas de concurrencia de Knowledge Hub truncan también
`django_migrations`; por eso el comando de regresión amplia usa una base
descartable, sin `--keepdb`. La suite final focalizada conserva correctamente el
registro y deja disponible la base para el smoke. No se alteró ese código heredado
de 01A/01B ni se reconstruyeron sus implementaciones.
