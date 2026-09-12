# MATERIAL-DATA — Closure

## Propósito

Cerrar la macrofase MATERIAL-DATA (01A–01J): desde el catálogo oficial ÖKOBAUDAT hasta
la contabilidad ambiental A1-A3 de materiales recibidos en obra, con gobernanza humana
explícita en cada punto de autoridad y trazabilidad histórica completa. Ninguna fase de
esta macrofase infiere equivalencia funcional, sustitución o recomendación de materiales:
eso queda reservado a **MATERIAL-INTELLIGENCE**, la siguiente macrofase.

## Arquitectura y flujo de datos completo

```
ÖKOBAUDAT (oficial, upstream)
   ↓ snapshot inmutable                                    [01A]
OekobaudatDataStockFact / OekobaudatProcessFact
   ↓ hidratación de detalle, snapshot inmutable             [01B]
OekobaudatEnvironmentalProfileFact + Indicator facts (A1-A3, GWP)
   ↓ evaluación determinística, construcción                [01C]
MaterialEnvironmentalFactorCandidate (global, inmutable, evidencia congelada)
   ↓ revisión humana explícita (superusuario)
MaterialFactorCandidateReview
   ↓ promoción                                              [01C]
FactorAmbiental (borrador, global) + VersionFactorAmbiental (borrador)
   ↓ activación mediante gobernanza EXISTENTE (factor_governance)
VersionFactorAmbiental ACTIVO
   ↓ mapeo explícito, tenant-scoped, con vigencia temporal   [01D]
MaterialFactorMapping (propuesto → aprobado, protegido contra solapamiento en PostgreSQL)
   ↓ EventoMaterial.RECEPCION (único punto contable A1-A3, sin cambios)
   ↓ elegibilidad determinística (mapping aprobado + version activa + unidad compatible)
   ↓ cálculo determinístico (Decimal, sin cambios al motor matemático)
CalculoAmbiental (inmutable, con recalculo_de protegido por constraint única)   [01G]
   ↓ selectores de sólo lectura sobre lo anterior:
   cobertura ambiental [01E] · calidad de dato [01F] · ledger A1-A3 [01G]
   · descubrimiento de catálogo [01H] · gobernanza de actualización de fuente [01I]
```

**Nunca**: `nombre parecido → factor adivinado → cálculo`. **Siempre**: `mapeo explícito
gobernado → factor gobernado → versión activa → elegibilidad determinística → cálculo`.
Verificado explícitamente en `test_material_factor_selector.py` (p. ej.
`test_exact_material_code_without_mapping_gives_no_factor`).

## Autoridades (una por invariante, sin duplicación)

| Invariante | Autoridad única | Fases que la consumen (sólo lectura) |
|---|---|---|
| Snapshot/typed fact oficial | `apps.knowledge` (01A/01B), sin cambios | 01C–01I |
| Elegibilidad y normalización A1-A3 de un perfil | `evaluate_material_profile()` (01C) | 01F, 01I (reutilizado, nunca reimplementado) |
| Selección del factor de cálculo para una recepción | `select_material_factor()` (01D) | 01E, E2E |
| Activación de una versión de factor | `factor_governance.transition_factor_version()` (preexistente) | Sin cambios; 01D/01E/01G sólo leen `estado` |
| Ledger de cálculos A1-A3 | `CalculoAmbiental` (preexistente, inmutable) | 01G añade selectores, no un segundo libro contable |
| Vigencia temporal de mapeo | `MaterialFactorMapping` + `EXCLUDE` constraint PostgreSQL (01D) | 01E–01G leen su estado, nunca lo mutan |

## Límite contable

`EventoMaterial.RECEPCION` sigue siendo el único punto donde se reconoce impacto A1-A3.
`uso/consumo/traslado/almacenamiento/sobrante/devolucion/reutilizacion/residuo/ajuste`
pueden alimentar trazabilidad y balance de stock (`material_balance`, sin cambios) pero
nunca vuelven a contabilizar A1-A3 — verificado en `test_material_calculation_catalog.py`
(`test_uso_no_es_punto_contable_...`) y en el E2E de 01J.

## Gobernanza y puntos de decisión humana

- **Candidato → revisión → promoción** (01C): superusuario global, sin cambios.
- **Activación de versión de factor**: gobernanza existente, sin cambios; 01D/01G nunca
  activan un factor automáticamente.
- **Mapeo material → factor** (01D): `propose_material_mapping`/`approve_material_mapping`
  requieren permisos de tenant explícitos (`MATERIAL_MAPPING_PROPOSE`/`_APPROVE`); un
  mapeo aprobado es inmutable salvo transición de estado (revocar/reemplazar).
- **Actualización de fuente** (01I): sólo clasifica (`no_impact`/`review_recommended`/
  `review_required`); nunca activa, revoca, recalcula o reescribe historia.

## Vigencia temporal del mapeo

Un mapeo aprobado responde a: qué material, qué factor, quién aprobó, cuándo, desde
cuándo, hasta cuándo. La selección usa la fecha efectiva del `EventoMaterial.RECEPCION`
(`select_material_factor`). Dos mapeos aprobados no pueden solaparse para el mismo
material: protegido con `EXCLUDE USING gist` en PostgreSQL (`material_mapping_no_overlap`,
migración `0068`), verificado con un test de concurrencia real de dos hilos.

## Calidad de dato ambiental

`assess_material_data_quality()`/`assess_factor_data_quality()` (01F) son funciones puras
sobre evidencia ya congelada por 01C (`initial_eligibility`/`normalization`/
`functional_context`): determinísticas, sin IA, sin score opaco. El eje de fallo duro
(`insufficient`) reutiliza literalmente `compatible`/`reasons` de 01C; nunca se inventa un
segundo criterio de elegibilidad.

## Semántica del ledger

`CalculoAmbiental` (preexistente) es el único libro contable; nunca se creó uno paralelo.
"Actual" = la fila que ninguna otra `recalculo_de` referencia. Un defecto de concurrencia
real preexistente se corrigió (`recalculo_de` sin unicidad permitía dos recálculos
concurrentes de la misma base) con una `UniqueConstraint` (migración `0069`) + traducción
a `ValidationError`; verificado con un test de concurrencia real de dos hilos que produce
exactamente un ganador.

## Gobernanza de actualización de fuente

01I nunca vuelve a consultar upstream: sólo compara la evidencia congelada de un candidato
contra lo que **ya** hidrataron los comandos de sincronización existentes de 01A/01B.
Al ser de sólo lectura, es idempotente y seguro ante concurrencia por construcción — sin
necesidad de un modelo nuevo ni de bloqueos.

## APIs (todas nuevas de esta macrofase; superusuario donde corresponde a gobernanza global,
tenant-scoped con 404 cruzado donde corresponde a datos de organización)

| Fase | Endpoint | Alcance |
|---|---|---|
| 01D | `organizaciones/<id>/mapeos-material-factor/...` (list/detail/aprobar/rechazar/revocar) | tenant |
| 01D | `organizaciones/<id>/materiales-operacionales/<id>/elegibilidad-calculo/` | tenant |
| 01E | `.../materiales-operacionales/cobertura-ambiental/`, `.../<id>/cobertura-ambiental/`, `.../eventos-materiales/<id>/cobertura-ambiental/` | tenant |
| 01F | `environmental-governance/material-factor-candidates/<id>/calidad/` | superusuario |
| 01G | `.../materiales-operacionales/ledger-a1a3/...` (totales/entradas/detalle) | tenant |
| 01H | `catalogo-material/`, `catalogo-material/<id>/` | cualquier usuario autenticado |
| 01I | `environmental-governance/material-factor-candidates/<id>/impacto-fuente/` | superusuario |

## Comandos operativos (documentados; NO ejecutados en producción)

```sh
# Ya existentes (01A-01C), sin cambios:
python manage.py sync_okobaudat_material_catalog
python manage.py hydrate_okobaudat_process_details
python manage.py build_okobaudat_material_factor_candidates

# Nuevo en 01I — de sólo lectura, idempotente, seguro de repetir:
python manage.py assess_okobaudat_material_updates [--status promoted_to_draft]

# Migraciones (0067-0069):
python manage.py migrate analytics
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Runbook de producción (para el gate humano, NO ejecutado por esta sesión)

1. `python manage.py check` y `makemigrations --check --dry-run` en el entorno destino.
2. `python manage.py migrate analytics` — aplica `0067` (esquema de mapeo),
   `0068` (extensión `btree_gist` + `EXCLUDE` constraint; requiere PostgreSQL, no-op en
   otro motor), `0069` (constraint única en `recalculo_de`).
3. Verificar que `btree_gist` se instaló: `\dx` en `psql` debe listarlo.
4. Ningún dato de producción fue tocado por esta sesión: ni mappings, ni activaciones,
   ni recepciones, ni cálculos.
5. La primera vez que un tenant quiera calcular un material, un usuario con permiso de
   propuesta debe crear un `MaterialFactorMapping` y alguien con permiso de aprobación
   debe aprobarlo explícitamente — no hay atajo automático, por diseño.

## Hallazgo de infraestructura de tests — CORREGIDO

Al ejecutar la regresión completa combinada (`apps.knowledge` + `apps.analytics`, 1125
tests) aparecieron ~29 fallos fuera de MATERIAL-DATA (`test_generated_emissions_indicator`,
`test_professional_v2`, `test_legal_applicability`, `test_requirements_compliance_contract`).
Causa raíz confirmada: el patrón `_fixture_teardown` de `TransactionTestCase` que hace
`TRUNCATE <todas las tablas> ... RESTART IDENTITY CASCADE` para aislar tests sobre una FK
legacy que `flush` no maneja — usado por **8 archivos preexistentes** además de los de
MATERIAL-DATA — borraba `django_migrations` mismo (rompiendo el siguiente `manage.py test
--keepdb`) y filas sembradas por migraciones de datos (p.ej. `EnvironmentalSource
codigo="bcn-leychile"`) sin restaurarlas, porque `emit_post_migrate_signal()` no corre y
esos datos no son señales post_migrate. Sólo `test_okobaudat_detail.py` excluía
`django_migrations` correctamente; los otros 7 no. **Corregido con alcance mínimo**
(excluir `django_migrations` del truncate + llamar `emit_post_migrate_signal`, replicando
el único patrón ya correcto) en: `test_legal_applicability.py`, `test_geospatial_context.py`,
`test_legal_evidence_mapping.py`, `apps/knowledge/test_geo_sources.py`,
`apps/knowledge/test_legal_evidence.py`, `apps/knowledge/test_okobaudat.py`,
`apps/knowledge/test_regulatory_context.py`. Confirmado con una regresión completa limpia
posterior: la corrupción de `django_migrations` desapareció y el error
`EnvironmentalSource... does not exist` desapareció (de 29 a 28 fallos, exactamente el
delta esperado). Justificación para tocar archivos ajenos a MATERIAL-DATA: bloqueaba
directamente el gate de regresión completa que 01J exige (regla de fallas: "bug previo real
que bloquea MATERIAL-DATA: corrígelo con alcance mínimo").

## Segundo hallazgo preexistente (confirmado, no de MATERIAL-DATA, no corregido: fuera de alcance)

Tres archivos ajenos a materiales (`test_professional_v2.py`, `test_generated_emissions_indicator.py`,
`test_requirements_compliance_contract.py`) fallan con `"Existen múltiples metodologías
aplicables con igual prioridad"` / `"Ningún método aplicable es calculable"` incluso
ejecutados **completamente solos** sobre una base de datos recién migrada, sin ningún
archivo de MATERIAL-DATA involucrado. Causa raíz identificada con certeza:
`apps/analytics/apps.py` conecta `ensure_environmental_catalog_after_migrate` a la señal
`post_migrate`, que siembra automáticamente metodologías **globales** (combustible/energía)
después de **cualquier** migración — incluida la de una base de test recién creada. Esas
metodologías globales, evaluadas por `methodology_selector.select_methodology()`, entran a
`applicable_candidates` (conjunto más amplio que "aplicable": incluye also
`no_calculable`/`requiere_revision`) para actividades de tipo `transporte` que no controla su
propio `aplicabilidad`, empatando en prioridad con la metodología tenant-scoped que cada test
crea y disparando la rama de ambigüedad. Esto es 100% preexistente e independiente de esta
macrofase: no se tocó `apps.py`, `signals.py`, `methodology_selector.py`,
`system_environmental_catalog.py` ni ninguno de los tres archivos de test (`git diff` vacío
en los cinco). Corregirlo requeriría cambiar la semántica de aplicabilidad/prioridad de
metodologías de transporte y combustible — dominio explícitamente fuera del alcance de
MATERIAL-DATA — por lo que se documenta y no se toca, según la política de fallas.

## Deuda técnica real (documentada, no bloqueante)

- `reception_coverage()` (01E) consulta la BD por cada recepción al construir un resumen
  agregado (`material_environmental_coverage`); correcto y sin N+1 *dentro* del cálculo de
  una recepción, pero sí una consulta por recepción a nivel de resumen. Sin evidencia de
  lentitud a la escala probada (decenas de recepciones); si un tenant agrega miles de
  recepciones por período, conviene batchear las consultas de mapping/versión activa antes
  del bucle. No se optimizó especulativamente (regla anti-overengineering).
- No se agregaron índices nuevos: no hubo evidencia de necesidad a la escala probada.
- El `EXCLUDE` constraint y el índice único parcial "anti-duplicado" de 01D viven en SQL
  crudo (`RunPython`), no en `Meta.constraints` de Django — mismo patrón que los triggers
  de 01C; `makemigrations --check` no los ve pero tampoco intenta revertirlos.
- En SQLite (sin PostgreSQL) la protección de solapamiento temporal de mapeos y la
  protección de recálculo concurrente dependen sólo de la capa de servicio, no de un
  constraint de base de datos — documentado, no oculto.

## Resultados finales verificados

- **E2E A2** (1000 kg, `0.847351015163189 kgCO2e/kg`, real fixture ÖKOBAUDAT) y
  **E2E A1** (2 m3, `-647.4201396839651 kgCO2e/m3`, signo negativo preservado): PASS,
  recorren la cadena completa y reconstruyen las 40 preguntas del DoD desde datos
  persistidos únicamente (`test_material_data_e2e.py`, 2/2).
- **Migraciones 0067-0069**: forward, reverse (a 0066) y forward de nuevo, limpio en
  PostgreSQL real.
- **Full regression final: 1097/1125 PASS** (`apps.knowledge` 163 + `apps.analytics` 962).
  Los 28 fallos restantes (1 FAIL + 27 ERROR) están **100% fuera de MATERIAL-DATA** — ver
  "Segundo hallazgo preexistente" arriba — y persisten incluso ejecutando esos 3 archivos
  completamente solos en una base recién migrada, sin ningún archivo de materiales
  presente. **Todos los tests de `test_material_*.py` y del E2E: 100% PASS.**
- `manage.py check`: limpio. `makemigrations --check --dry-run`: sin cambios pendientes.
  `git diff --check`: sin conflictos (sólo avisos LF→CRLF de Windows).

## Frontera respetada

Ningún archivo de esta macrofase implementa fuzzy matching, embeddings, RAG, scoring,
ranking, sustitución, equivalencia funcional automática, A4/A5, logística o
recomendación. Verificado explícitamente con tests negativos (`test_never_ranks_or_scores_results`,
la batería completa de `test_material_factor_selector.py`).
