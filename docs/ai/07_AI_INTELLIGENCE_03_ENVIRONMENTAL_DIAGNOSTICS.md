# AI-INTELLIGENCE-03 — Diagnóstico ambiental explicable y recomendaciones asistidas

## Objetivo

Construir una capa de diagnóstico ambiental **determinista** sobre la capa
analítica de AI-INTELLIGENCE-02, capaz de detectar automáticamente
situaciones relevantes en una obra y explicarlas usando exclusivamente
datos reales, umbrales configurables y evidencia trazable.

La IA **no calcula** indicadores, **no infiere** anomalías, **no declara**
cumplimiento normativo y **no inventa** recomendaciones. Su función es
únicamente: **detectar → priorizar → explicar → recomendar revisión**.
Todo lo que aparece en un hallazgo (`finding`) fue calculado por Python
determinista antes de que el LLM lo viera.

## Arquitectura

```
Datos operacionales (EventoMaterial, Observacion, RegistroFlujoAmbiental, EvaluacionCalidadDato)
        ↓
apps.ai.analytics_tools (AI-INTELLIGENCE-02) — series, agregados, rankings, evidencia
        ↓
apps.ai.diagnostics (AI-INTELLIGENCE-03) — engine.py + rules.py + scoring.py + serializers.py + evidence.py
        ↓
apps.ai.tools.diagnose_environmental_performance — thin adapter (resolución de obra + RBAC)
        ↓
LLM (orchestrator) — sólo redacta e interpreta los findings ya calculados
```

`analytics != diagnostics != LLM` se mantiene en tres módulos separados,
nunca mezclados:

| Módulo | Responsabilidad | Nunca hace |
|---|---|---|
| `apps/ai/analytics_tools.py` (AI-02, sin cambios) | Series, agregados, rankings físicos/impacto | Clasificar severidad, priorizar |
| `apps/ai/diagnostics/rules.py` | Clasificar números ya calculados contra umbrales fijos → `DiagnosticFinding` o `None` | Consultar la base de datos, llamar al LLM |
| `apps/ai/diagnostics/engine.py` | Orquestar: pedir números a `analytics_tools`, correr las reglas, ordenar por prioridad | Calcular un total/promedio/ranking él mismo |
| `apps/ai/diagnostics/scoring.py` | `priority_score` puro (severidad + modificadores) | Decidir si algo es un hallazgo |
| `apps/ai/diagnostics/evidence.py` | Agregación de evidencia/calidad/factor sobre uno o varios materiales (compartida con `get_evidence_quality` de AI-02 — nunca duplicada) | — |
| `apps/ai/diagnostics/serializers.py` | `DiagnosticFinding` → dict JSON-serializable | — |
| `apps/ai/tools.py::diagnose_environmental_performance` | Resolver obra (id o nombre), RBAC, invocar el engine | Cualquier cómputo |

Ningún módulo de `diagnostics/` importa el LLM ni el orquestador; el
paquete es reutilizable fuera del agente de IA (p. ej. desde un futuro
endpoint REST) sin cambios.

### Períodos de comparación

`apps/ai/periods.py::resolve_comparison_periods` calcula **current** y
**previous** (mismo largo, inmediatamente anterior) de forma determinista:
sin argumentos, usa "este mes calendario vs el mes calendario anterior";
con `date_from/date_to/relative_months`, resuelve el período actual (vía
`resolve_period`, ya existente en AI-02) y calcula el anterior de igual
duración. Mismos argumentos → mismos límites de fecha, sin importar qué
LLM (o ningún LLM) esté detrás.

### Qué reutiliza de AI-INTELLIGENCE-02 (nunca duplicado)

- `analytics_tools.operational_aggregate` — total/promedio/máx/mín/variación por período (para DIAG-01/02/11/12).
- `analytics_tools.rank_operational_entities` — ranking por obra/material/activo/período, en ambos dominios (físico e impacto) (para DIAG-03/04/09/10).
- `analytics_tools.operational_timeseries` — serie mensual con huecos visibles (`con_datos`) (para DIAG-11/12).
- `apps.analytics.services.material_factor_selector.select_material_factor` — estado de mapeo de factor (para DIAG-06), sin decidir un factor.
- `apps.analytics.services.material_quality.assess_factor_data_quality` — calidad del factor (sin cambios).
- La única pieza nueva de bajo nivel es `apps/ai/diagnostics/evidence.py::gather_evidence_stats`, que generaliza (nunca duplica) la consulta que ya usaba `get_evidence_quality` de AI-02 para operar sobre **varios** materiales de una categoría en vez de uno solo — `get_evidence_quality` fue refactorizado para llamar a esta misma función, sin cambiar su salida.

## Reglas (`rules.py`)

Cada regla es una función pura: recibe números ya calculados y devuelve un
`DiagnosticFinding` o `None`. Ninguna regla toca la base de datos.

| Código | Regla | Dispara cuando | Severidad |
|---|---|---|---|
| `NEW_ACTIVITY` | DIAG-01/02 (caso especial) | `previous == 0` y `current != 0` | `info` |
| `CONSUMPTION_INCREASE` | DIAG-01 | `variation_percent >= 20/40/75` | `medium`/`high`/`critical` |
| `CONSUMPTION_DECREASE` | DIAG-02 | `variation_percent <= -20` | siempre `info` (nunca "mejora") |
| `IMPACT_CONCENTRATION` | DIAG-03 | un material concentra `>=50/65/80%` del impacto (kgCO2e) de la obra | según tramo |
| `CONSUMPTION_CONCENTRATION` | DIAG-04 | un activo/material concentra `>=50/65/80%` del consumo físico de una métrica | según tramo |
| `CHANGE_DRIVER_ACTIVO` | DIAG-09 | tras una variación, un activo explica `>=50%` del delta total | `medium`/`high` |
| `CHANGE_DRIVER_MATERIAL` | DIAG-10 | ídem, para materiales | `medium`/`high` |
| `HIGH_VARIABILITY` | DIAG-11 | `CV = std_dev/mean >= 0.5` sobre los períodos con datos | `medium`/`high` |
| `INCOMPLETE_COVERAGE` | DIAG-12 | `periodos_con_datos < periodos_totales` en la ventana analizada | `medium` |
| `MISSING_EVIDENCE` | DIAG-05 | cobertura de evidencia `< 80%` | `medium`/`high` |
| `UNMAPPED_FACTOR` | DIAG-06 | algún material de la categoría no tiene factor mapeado (`select_material_factor` no calculable) | `high` |
| `LOW_DATA_QUALITY` | DIAG-07 | `>= 20%` de las observaciones evaluadas están en un estado pobre de `EvaluacionCalidadDato` (reutiliza la escala existente, nunca una nueva) | `medium`/`high` |
| `UNSUPPORTED_DATA` | DIAG-08 | un registro no tiene evidencia **y** su observación tiene calidad pobre, simultáneamente | `high`/`critical` |

`DIAGNOSTIC_RULESET_VERSION = "1.0"` viaja en cada respuesta
(`ruleset_version`) para poder cambiar umbrales después sin perder
trazabilidad de qué versión produjo un hallazgo histórico.

## Umbrales (centralizados en `rules.py`, nunca inline)

```python
VARIATION_THRESHOLDS = {"medium": 20.0, "high": 40.0, "critical": 75.0}
CONCENTRATION_THRESHOLDS = {"medium": 50.0, "high": 65.0, "critical": 80.0}
EVIDENCE_COVERAGE_THRESHOLD = 80.0
DATA_QUALITY_POOR_SHARE_THRESHOLD = 20.0
VARIABILITY_CV_THRESHOLD = 0.5
MIN_ENTITIES_FOR_CONCENTRATION = 2
```

`DATA_QUALITY_POOR_STATES` reutiliza literalmente los estados ya
existentes de `EvaluacionCalidadDato.Estado` (`incompleto`,
`requiere_revision`, `no_confiable`, `no_calculable`) — nunca se inventó
una escala nueva.

## Priorización (`scoring.py`)

```python
SEVERITY_BASE_SCORE = {"critical": 100, "high": 75, "medium": 50, "low": 25, "info": 10}
# Modificadores (aditivos, resultado siempre capado a 100):
UNMAPPED_FACTOR            +20
MISSING_EVIDENCE/UNSUPPORTED_DATA +15
variation_percent >= 75    +20
share_percent > 60         +15
affected_count > 10        +10
```

`compute_priority(finding)` es una función pura de los campos ya fijados
del `finding` — mismo finding, mismo score, siempre.

## Ejemplo real (tenant demo, "Edificio Horizonte Norte", ventana por defecto)

```json
{
  "code": "IMPACT_CONCENTRATION",
  "severity": "critical",
  "priority_score": 100,
  "title": "Concentración de impacto ambiental: Hormigón H30",
  "description": "\"Hormigón H30\" concentra el 97.9% del impacto de impacto_ambiental_total en el período.",
  "reason": {"rule": "share_percent >= 50.0", "observed": 97.9, "threshold": 50.0},
  "drivers": [{"entity_type": "material", "entity_id": 62, "name": "Hormigón H30", "contribution_percent": 97.9}],
  "recommendations": ["Priorizar acciones de reducción sobre la entidad que concentra el impacto."]
}
```

## Restricciones explícitas (verificadas en tests y en el smoke real)

- El LLM **nunca** calcula un total/variación/ranking/CV — todo llega ya
  resuelto en `finding`.
- El LLM **nunca** reclasifica severidad ni umbral — sólo los presenta.
- Una disminución (`CONSUMPTION_DECREASE`) es siempre `severity="info"` y
  su descripción nunca usa "mejora"/"eficiencia" — normalizar contra
  producción/actividad excede el alcance de esta capa.
- `evidencia`, `calidad del dato` y `factor ambiental` son tres hallazgos
  distintos (`MISSING_EVIDENCE`, `LOW_DATA_QUALITY`, `UNMAPPED_FACTOR`) —
  nunca combinados en una sola afirmación (continuación directa del fix
  de AI-INTELLIGENCE-02, ahora generalizado a nivel de categoría/obra).
- Las recomendaciones **sólo** salen de `RECOMMENDATIONS` (catálogo fijo
  en `rules.py`) — el LLM puede redactarlas mejor pero no inventar una
  acción regulatoria, un responsable, o un reemplazo de maquinaria no
  presente en el catálogo.
- **Nunca** se declara cumplimiento normativo: no existe una regla
  `COMPLIANCE_*` en este catálogo, y el system prompt lo prohíbe
  explícitamente incluso dentro de un diagnóstico.
- `cantidad física` (m³/L/kWh/kg) e `impacto kgCO2e` nunca se mezclan en
  un mismo finding: `CONSUMPTION_CONCENTRATION`/`CONSUMPTION_INCREASE` son
  siempre físicos; `IMPACT_CONCENTRATION` es siempre impacto.

## RBAC y aislamiento de tenant

`diagnose_environmental_performance` (el único punto de entrada desde el
LLM) reutiliza exactamente el mismo patrón que toda tool obra-scoped de
AI-01/02: `_guarded(user, organization, Permission.DATA_VIEW)` +
`_resolve_obra` (que aplica `require_work_access`, RBAC por obra
específica) antes de tocar `engine.py`. El engine mismo no vuelve a
verificar permisos — por diseño, sólo consume fuentes ya guardadas
(`analytics_tools`, que ya intersecta contra `filter_works_for_user` para
cualquier ranking cruzado de obras). Una obra de otro tenant o una obra
fuera del alcance de un usuario `alcance=OBRAS` siempre devuelve
`not_found`, nunca datos parciales.

## Tests (`apps/ai/tests/test_diagnostics.py`, 52 pruebas — objetivo mínimo 30 superado)

- **Reglas puras** (sin BD): aumento sobre/bajo umbral, tramo crítico,
  `previous == 0` (nueva actividad), caída siempre informativa, división
  por cero evitada, concentración sobre/bajo umbral y con mínimo de
  entidades, atribución de cambio correcta e incorrecta, variabilidad
  alta/baja e insuficientes puntos, cobertura incompleta/completa,
  evidencia faltante/completa/sin registros, factor no mapeado,
  calidad baja, datos sin respaldo (incluyendo severidad crítica),
  evidencia y factor como códigos distintos.
- **Scoring**: score base por severidad, modificadores individuales,
  suma capada a 100.
- **Motor + tool** (BD real, tenant demo): resolución de obra por nombre,
  argumento faltante, obra inexistente (`ok=True, status=not_found`),
  RBAC denegado sin permiso, obra fuera de alcance (`alcance=OBRAS`),
  aislamiento cross-tenant, período sin datos, orden por prioridad
  descendente, cada finding con período/entidad/razón, driver
  verificado contra `rank_operational_entities` real (no inferido),
  determinismo (mismo input → mismo output), catálogo de recomendaciones
  respetado, versión de ruleset presente, schema de la tool registrado.

Gates verificados: `apps.ai` completo **134/134** (82 de AI-01/02 +
52 nuevas), `manage.py check` limpio, `makemigrations --check --dry-run`
sin cambios.

## Smoke real (OpenRouter, `google/gemini-2.5-flash`, tenant `DEMO_HORIZONTE`)

| # | Pregunta | Tool chain | Findings backend (top) | ¿Grounded? |
|---|---|---|---|---|
| 1 | ¿Qué debería preocuparme de esta obra este mes? | `diagnose_environmental_performance` | 12 findings: `IMPACT_CONCENTRATION` (crítico, Hormigón H30 97.9%), `CONSUMPTION_INCREASE` combustible/materiales (crítico), `UNMAPPED_FACTOR`, 3×`MISSING_EVIDENCE`, `CONSUMPTION_CONCENTRATION` (Excavadora 68.1%) | ✅ sí — cada cifra citada aparece literal en el finding |
| 2 | ¿Qué cambió más respecto del mes anterior? | `diagnose_environmental_performance` | mismos 12; el modelo identificó correctamente combustible/materiales (+100%) y el driver (Hormigón H30, 100% de la variación) | ✅ sí |
| 3 | ¿Cuál es la principal fuente de impacto? | `diagnose_environmental_performance` | `IMPACT_CONCENTRATION` primero (score 100) | ✅ sí — respuesta lidera con el finding de mayor prioridad |
| 4 | ¿Hay problemas con la evidencia? | `diagnose_environmental_performance` | `MISSING_EVIDENCE` combustible/materiales, distinto de `UNMAPPED_FACTOR` | ✅ sí — nunca conflacionados |
| 5 | ¿Hay datos que no deberían usarse todavía para calcular emisiones? | `resolve_entity` → `diagnose_environmental_performance` | `UNMAPPED_FACTOR` + `MISSING_EVIDENCE` citados como la respuesta a "no deberían usarse todavía" | ✅ sí |
| 6 | ¿Qué debería revisar primero? | `diagnose_environmental_performance` | Presentado en el orden real de `priority_score` (crítico → alto → medio → info) | ✅ sí |

En los seis casos la respuesta final es una redacción de los `findings`
devueltos por el backend — ninguna cifra, porcentaje o umbral fue
generado por el modelo. El transcript completo de este smoke se conservó
localmente durante el desarrollo (no se persiste ningún dato real de
cliente: tenant 100% sintético).

## Limitaciones conocidas

- `CONSUMPTION_CONCENTRATION`/`CHANGE_DRIVER_ACTIVO` (atribución por
  activo) sólo existen para la métrica `combustible` en el modelo de
  datos actual (`RegistroFlujoAmbiental.activo` es el único lugar del
  esquema con atribución confiable por activo — confirmado en el audit de
  AI-INTELLIGENCE-02). Agua/energía/residuos no tienen desglose por
  activo hasta que el esquema/seed lo modele.
- La ventana de variabilidad (`HIGH_VARIABILITY`) usa los meses
  disponibles entre el período anterior y el actual; con historia muy
  corta (el tenant demo tiene 4 meses) el CV puede no ser representativo
  — el propio finding no se dispara si hay menos de 2 puntos con datos.
  `INCOMPLETE_COVERAGE` siempre acompaña a esta limitación cuando aplica.
- `DIAG-02` (caída) nunca se presenta como mejora porque este sistema no
  normaliza contra producción/actividad — si en el futuro existe esa
  normalización, esta regla debería revisarse, no reinterpretarse en el
  prompt.
- El resultado no se persiste (no hay modelo `DiagnosticRun`): se
  devuelve en la respuesta de la tool (`ruleset_version` incluido) y en
  `Message.tool_result`/`Message.provenance`, igual que cualquier otro
  resultado de tool de AI-01/02. Una futura auditoría persistente
  (`diagnostic_run_id`, `rules_version`, timestamp) es una extensión
  aislada, no un cambio de este contrato.
