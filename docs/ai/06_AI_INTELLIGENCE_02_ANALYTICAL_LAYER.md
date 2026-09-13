# AI-INTELLIGENCE-02 — Capa de herramientas analíticas

## 1. Diagnóstico (causa raíz)

AI-INTELLIGENCE-01 sólo expuso herramientas de **búsqueda puntual**: una
entidad, un estado actual (`get_project_summary`, `get_material_summary`,
`get_emissions_summary` con un filtro de obra fijo, etc.). No existía
ninguna herramienta para:

1. una **serie temporal** (valores por mes/período),
2. una **agregación estadística** (total/promedio/máximo/mínimo/variación),
3. un **ranking cruzado de entidades** (obras, materiales, activos, períodos), ni
4. la **resolución de una referencia en lenguaje natural** (nombre de obra,
   material o maquinaria) contra los datos reales del tenant.

Por eso, ante preguntas de comparación/agregación/ranking, el modelo tenía
sólo dos salidas posibles: calcular él mismo el número (prohibido
explícitamente por el system prompt) o admitir que no podía — y, al no
tener forma de resolver un nombre a un id, terminaba pidiéndole al usuario
"dame el ID" o "dime cuáles obras existen", algo que el propio sistema ya
podía resolver.

Una causa raíz, no cuatro preguntas distintas — por eso la solución es una
capa arquitectónica nueva, no cuatro parches puntuales.

## 2. Dos dominios de datos reales (hallazgo del audit)

El tenant modela el "consumo operacional" (agua, combustible, energía,
residuos, materiales) de **dos formas distintas**, ya existentes, nunca
duplicadas por esta macrofase:

| Dominio | Modelo/servicio ya existente | Qué mide | Atribución por activo |
|---|---|---|---|
| **Impacto material (A1-A3)** | `EventoMaterial` → `CalculoAmbiental`, `material_ledger.material_ledger_totals` | Impacto ambiental calculado (kgCO2e) | No |
| **Consumo físico por categoría** | `EventoMaterial`/`Observacion` (`concepto="cantidad_material"`), `MaterialOperacional.categoria` | Cantidad física real (m³, L, kWh, kg) | No (M2M opcional, no confiable) |
| **Flujo ambiental por activo** | `RegistroFlujoAmbiental.activo`, `sector_flows_v1.sector_summary` | Cantidad física por activo/maquinaria | Sí — único lugar del esquema con esta atribución |

`material_ledger_totals` (el primitivo reusado mencionado en la misión)
sólo suma el **impacto calculado** (`CalculoAmbiental.resultado`, siempre en
kgCO2e) — no la cantidad física. Por eso se agregó
`material_ledger.material_physical_totals` (extensión mínima y justificada,
mismo patrón de `group_by` que la función existente, misma tabla
`EventoMaterial`, sólo suma un campo distinto: `Observacion.valor_numerico`
en vez de `CalculoAmbiental.resultado`). Ninguna lógica de agregación se
duplicó — ambas funciones comparten `_dimension_key`, `Decimal`,
`defaultdict`.

Para "qué maquinaria consumió más combustible" no existía NINGÚN dato de
atribución por activo en el tenant demo (el M2M
`ActividadOperacional.activos` es opcional y no exclusivo). Se extendió el
seed (`seed_ai_demo_tenant.py::_machinery_history`) con dos
`ActivoOperacional` reales y sus `RegistroFlujoAmbiental` (granularidad
`ACTIVO`+`PUNTO`, la única combinación del modelo que permite atar un
activo a una obra simultáneamente — confirmado leyendo
`RegistroFlujoAmbiental.clean()`).

## 3. Arquitectura nueva

```
apps/ai/
  periods.py           # resolución determinista de "últimos N meses" (server-side, nunca por el LLM)
  metrics.py            # "agua"/"combustible"/... -> categoria (dominio físico) o Flujo (dominio por activo)
  resolvers.py           # nombre libre -> obra/material/activo real del tenant (RBAC-aware, nunca cross-tenant)
  analytics_tools.py     # operational_timeseries / operational_aggregate / rank_operational_entities / compare_projects
  tools.py               # adaptadores delgados (igual patrón que las 14 tools de AI-INTELLIGENCE-01)

apps/analytics/services/material_ledger.py
  + material_physical_totals(...)   # extensión mínima: cantidad física, no impacto
```

Nuevas tools registradas (`apps/ai/tools.py::TOOLS`):

| Tool | Qué resuelve |
|---|---|
| `resolve_entity` | nombre libre → obra/material/activo real (o "ambiguous"/"not_found") |
| `get_operational_timeseries` | serie mensual de una métrica/material/obra |
| `get_operational_aggregate` | total/promedio/máximo/mínimo/variación/cobertura |
| `rank_operational_entities` | ranking por obra/material/categoria/activo/periodo |
| `compare_projects` | ranking de TODAS las obras accesibles + "por qué" (hotspot) |
| `get_evidence_quality` (extendida) | 4 ejes distintos: registro/evidencia/calidad/factor; acepta nombre de material, no sólo id |

Regla de diseño en cada una: **el backend calcula, el LLM presenta**. Cada
función de `analytics_tools.py` hace toda la suma/orden/estadística en
Python sobre datos ya persistidos; el resultado es un dict plano con
`entidad, metrica, valor, unidad, periodo, comparacion, provenance,
calidad, cobertura` — nunca una expresión que el modelo deba evaluar.

### Corrección RBAC encontrada y corregida

Ni `material_ledger_totals(group_by="obra")` ni `material_physical_totals`
filtran por usuario — devuelven todas las obras del tenant. Un usuario con
`alcance=OBRAS` (acceso restringido a ciertas obras) podría, sin esta
corrección, ver el ranking de una obra a la que no tiene acceso.
`rank_operational_entities`/`compare_projects` intersectan siempre el
resultado contra `filter_works_for_user(...)` antes de mostrarlo al LLM —
cubierto por
`test_obra_scoped_user_never_sees_a_restricted_obra_in_ranking`.

### Límite de iteraciones de tools

`AI_MAX_TOOL_ITERATIONS` subió de 4 a 8 (`config/settings.py`,
`.env.example`) — una cadena real (resolver obra → resolver material/
categoría → serie/ranking → comparar → provenance) puede necesitar más de
4 llamadas en un mismo turno.

## 4. Tabla de verificación — las 4 preguntas reales

Ejecutado contra el tenant `DEMO_HORIZONTE` real, con OpenRouter real
(`google/gemini-2.5-flash`, el mismo modelo ya validado en
AI-INTELLIGENCE-01), no simulado.

| # | Pregunta original | Tool chain ejecutada | Respuesta anterior (reportada por el usuario) | Respuesta nueva (real, este smoke) | Resultado |
|---|---|---|---|---|---|
| 1 | ¿Cuál es la obra con mayor impacto ambiental y por qué? | `compare_projects()` | No podía comparar obras automáticamente | *"La obra con mayor impacto ambiental es 'Edificio Horizonte Norte', con un total de 470,691.00 kgCO2e. La razón principal... es 'HORIZONTE-HORMIGON', que contribuye con 460,800.00 kgCO2e (97.90%)."* | **PASS** |
| 2 | ¿Cuál es el consumo total de agua de Edificio Horizonte Norte en los últimos 3 meses? | `resolve_entity(obra)` → `get_operational_aggregate(metric=agua, relative_months=3)` | No podía agregar por material+período | *"El consumo total de agua en Edificio Horizonte Norte durante los últimos 3 meses fue de 540 m³."* | **PASS** |
| 3 | ¿Cuál fue el mes con mayor consumo de agua en Edificio Horizonte Norte? | `resolve_entity(obra)` → `rank_operational_entities(entity_type=periodo, metric=agua)` | No podía agrupar por mes/rankear | *"El mes con mayor consumo de agua... fue junio de 2026, con un total de 180 m³."* (los 3 meses están empatados en 180 m³ — la tool lo refleja, ver `test_empate_de_ranking_is_never_silently_broken`) | **PASS** |
| 4 | ¿Qué maquinaria de Edificio Horizonte Norte consumió más combustible? | `resolve_entity(obra)` → `rank_operational_entities(entity_type=activo, metric=combustible)` | No existía maquinaria como entidad separada | *"La maquinaria que consumió más combustible... fue la 'Excavadora Hidráulica EX-14', con un consumo de 1280 litros."* | **PASS** |
| — | ¿Qué evidencia respalda el consumo de agua de Edificio Horizonte Norte? (requisito 7, bug reportado) | `resolve_entity(obra)` → `get_evidence_quality(material="agua")` | *"no hay evidencia o factor ambiental"* (conflación) | *"se han registrado 3 eventos de consumo... no existe evidencia operacional adjunta... la calidad del dato... 'confiable con observaciones'... existe un factor mapeado, pero su calidad requiere revisión..."* — 4 ejes ya nunca combinados | **PASS** |

## 5. Tests nuevos (`apps/ai/tests/test_analytical_tools.py`, 25 pruebas)

Además de las 4 preguntas reales (a nivel de tool, sin red): período sin
datos, unidad incompatible (nunca mezclada), entidad inexistente, nombre
ambiguo, una sola obra, cross-tenant, obra restringida por RBAC, datos
incompletos (gap real del seed, visible como `con_datos: false`), empate de
ranking, más pruebas unitarias de `periods.py` y `resolvers.py`.

## 6. Gates verificados

- `apps.ai` completo: **81/81** (56 preexistentes + 25 nuevas), sin
  modificar ningún test de AI-INTELLIGENCE-01.
- `manage.py check`: sin incidencias.
- `makemigrations --check --dry-run`: sin cambios pendientes (ninguna
  migración nueva — sólo funciones de servicio, ningún modelo cambiado).
- Smoke real con OpenRouter: las 4 preguntas + la pregunta de evidencia,
  documentadas arriba, ejecutadas contra el tenant demo real.
- Aislamiento de tenant y RBAC: cubiertos explícitamente en los tests
  nuevos (`test_cross_tenant_ranking_never_leaks_another_orgs_obra`,
  `test_obra_scoped_user_never_sees_a_restricted_obra_in_ranking`).
- No se commiteó ni se hizo push — pendiente de aprobación explícita del
  usuario.
