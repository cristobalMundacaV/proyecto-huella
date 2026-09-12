# AI-INTELLIGENCE-01 — Operación y contrato interno

## Alcance

Asistente conversacional de solo lectura sobre los datos reales del tenant
actual. El LLM nunca consulta la base de datos directamente: cada turno
pasa por herramientas backend acotadas, tenant-verificadas y de solo
lectura. No hay escritura, aprobación ni cierre de nada desde el chat.

## Proveedor (`apps/ai/providers.py`)

`AIProvider` es la interfaz mínima (`name`, `model`, `available`,
`chat(messages, tools=None) -> AIChatResult`). `OpenRouterProvider` es la
única implementación; llama al SDK `openai` apuntado a
`OPENROUTER_BASE_URL` (patrón ya usado en `apps/analytics/services/
openrouter_document_provider.py`, no inventado). Cambiar de proveedor en
el futuro significa escribir una clase nueva con esa misma interfaz — el
orquestador, las tools y el system prompt no cambian.

### Variables de entorno (raíz `.env`, no `backend/.env`)

| Variable | Significado |
|---|---|
| `OPENROUTER_ENABLED` | `false` por defecto; bloquea cualquier llamada real |
| `OPENROUTER_API_KEY` | ya declarada por `DOCUMENT_AI_PROVIDER=openrouter`; compartida, nunca en frontend/logs/repositorio |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` por defecto |
| `OPENROUTER_MODEL` | sin default — debe configurarse explícitamente (nunca hardcodeado) |
| `AI_REQUEST_TIMEOUT_SECONDS` | timeout de la llamada al proveedor (default 30) |
| `AI_MAX_OUTPUT_TOKENS` | límite de tokens de salida por llamada (default 1200) |
| `AI_TEMPERATURE` | temperatura del modelo (default 0.2) |
| `AI_MAX_TOOL_ITERATIONS` | máximo de rondas tool-call por turno (default 4) — nunca un bucle infinito |
| `AI_MAX_MESSAGES_PER_CONVERSATION` | límite duro por conversación (default 200) |
| `AI_MAX_REQUESTS_PER_ORG_PER_HOUR` | límite de turnos de asistente por organización por hora (default 60) |

**Nota real de esta implementación**: `config/settings.py` sólo carga
`load_dotenv(PROJECT_ROOT / ".env")` (raíz del repo). Un archivo
`backend/.env` distinto (también gitignorado) puede existir con estas
mismas variables, pero Django nunca lo lee — es el mismo patrón exacto ya
documentado en `docs/integrations/ec3/04_VERIFICATION.md` para
`EC3_API_TOKEN`. Verificar siempre contra el `.env` de raíz.

### Reglas de proveedor cumplidas

Key sólo backend (nunca en el frontend, nunca en logs, nunca en DB —
`Message` no tiene ningún campo de credencial); timeout configurable;
reintentos acotados (2 intentos ante error de red/timeout, backoff
implícito del propio SDK); errores seguros (`AIProviderError.code`/`detail`
son siempre strings cortos y genéricos, nunca el mensaje crudo del
proveedor ni la API key); modelo configurable sin default hardcodeado;
temperature/max_tokens configurables.

## System prompt (`apps/ai/system_prompt.py`)

Versionado (`SYSTEM_PROMPT_VERSION`), testeado por presencia de frases
obligatorias (`apps/ai/tests/test_system_prompt.py`). Principios: nunca
inventar métricas/factores/cumplimiento/evidencia; nunca presentar un
candidato EC3 como aprobado si no está `MAPPED`; nunca presentar una
oportunidad como decisión constructiva; distinguir hechos/inferencias/
recomendaciones; explicitar cuando falta información; explicar
provenance; advertir problemas de calidad de datos; lenguaje profesional
y accionable. Ver `docs/ai-context/07_AI_IOT_AND_KNOWLEDGE.md` — el mismo
principio ("la IA no es fuente primaria") ya gobernaba el resto del
producto; este system prompt lo aplica al chat conversacional.

## Tools (`apps/ai/tools.py`)

14 herramientas de solo lectura, cada una un adaptador delgado sobre un
servicio ya existente (`ContextGateway`, `material_hotspots`,
`material_opportunities`/`material_ledger`, `material_quality`, `apps.ec3`,
`apps.knowledge`) — ninguna reimplementa agregación propia. Contrato común:
firma `(organization, user, **arguments)`, retorna
`{"ok": true, "data": {...}}` o `{"ok": false, "error": "...", "reason": "..."}`
(`not_found`, `permission_denied`, `missing_argument`, `unknown_tool`,
`invalid_arguments`) — nunca lanza una excepción hacia el orquestador
(`execute_tool` la atrapa). Cada tool valida el permiso RBAC más específico
para su dominio (`Permission.WORK_VIEW`, `INDICATOR_VIEW`,
`MATERIAL_MAPPING_VIEW`, `EVIDENCE_VIEW`, `PROBLEM_VIEW`, `FACTOR_VIEW`,
`DATA_VIEW`) antes de tocar cualquier dato, y todo `material_id`/`obra_id`
se resuelve siempre filtrando por la organización actual (nunca por un ID
"confiado" del LLM).

| Tool | Servicio reutilizado |
|---|---|
| `get_current_organization` | — (serializa `Organizacion`) |
| `list_projects` | `filter_works_for_user` |
| `get_project_summary` | `ContextGateway.work` → `construction_v1.work_context` |
| `get_environmental_indicators` | `IndicadorAmbiental`/`ValorIndicador` |
| `get_emissions_summary` | `material_ledger.material_ledger_totals` |
| `get_material_summary` | `ContextGateway.material_intelligence` |
| `get_material_hotspots` | `material_hotspots.material_hotspots` |
| `get_evidence_quality` | `select_material_factor` + `material_quality.assess_factor_data_quality` |
| `get_open_alerts` | `ProblematicaAmbiental` (el "alerta" moderno; nunca `AlertaCumplimientoAmbiental` legacy) |
| `get_ec3_mapping_status` | `apps.ec3.models.Candidate` + `apps.ec3.services.candidate_data` |
| `get_ec3_opportunities` | `apps.ec3.opportunity.material_candidate_opportunities` |
| `get_factor_provenance` | `material_ledger.ledger_entry_provenance` |
| `get_historical_trends` | `ContextGateway.indicator_history` |
| `search_environmental_knowledge` | `apps.knowledge` (`EnvironmentalSource`/`ExternalRecord`, no tenant-scoped: base de conocimiento compartida) |

## Orquestador (`apps/ai/orchestrator.py`)

`run_turn(conversation, organization, user, user_message, provider)`:
persiste el mensaje del usuario → arma el historial acotado (últimos 20
mensajes user/assistant con contenido, nunca reproduce tool-calls de
turnos anteriores) → antepone el system prompt → llama al proveedor con
el esquema de las 14 tools → si el modelo pide tool(s), cada una se
ejecuta vía `execute_tool` (nunca una excepción sin capturar) y su
resultado se persiste y se reenvía al modelo → se repite hasta
`AI_MAX_TOOL_ITERATIONS` (nunca un bucle infinito) o hasta una respuesta
final de texto. `validate_ai_operation(IntelligenceOperation.READ_CONTEXT)`
(política ya existente en `apps/analytics/policies/intelligence.py`) se
invoca al inicio de cada turno — reutiliza la gobernanza de autoridad IA
ya establecida, no un mecanismo paralelo.

## Guardrails

De solo lectura por diseño: ninguna tool escribe. Si el usuario pide una
acción (aprobar una EPD, cerrar una alerta, cambiar un factor), el system
prompt exige explicar que requiere intervención humana en el flujo
correspondiente de Carbono Zero y dar la guía — nunca simular que se
ejecutó. Ver `docs/ai/02_DEMO_QUESTIONS_AND_EXPECTED_BEHAVIOR.md`,
preguntas 14-16, para los tres casos límite explícitos (cumplimiento
normativo, aprobación automática, acceso cross-tenant).

## Aislamiento de tenant y RBAC

Cero mecanismo nuevo: cada endpoint resuelve la organización vía
`organizacion_id` en la URL (protegido además por el
`OrganizacionTenantMiddleware` ya existente, que devuelve 401/404 antes de
llegar a la vista) y cada tool re-verifica pertenencia al filtrar por
`organizacion=organization` explícitamente. `Conversation`/`Message` llevan
`organizacion` y `usuario` desde su creación y nunca se reasignan. Permiso
nuevo, mínimo: `Permission.INTELLIGENCE_CHAT_VIEW` (`intelligence_chat.view`),
incluido en `VIEW_PERMISSIONS` — todos los roles existentes lo heredan
automáticamente, igual que cualquier otro permiso de sólo lectura. Pruebas
explícitas cross-tenant en `apps/ai/tests/test_tenant_isolation.py` (incluye
el caso de un LLM "malicioso" pidiendo un `material_id` de otra
organización — la tool lo rechaza igual).

## Modelo de conversación (`apps/ai/models.py`)

`Conversation` (organización + usuario + obra opcional, nunca reasignables)
y `Message` (append-only: `save()`/`delete()` y el queryset personalizado
lanzan `ValidationError` ante cualquier intento de mutar/borrar un mensaje
ya creado — el historial del chat nunca se reescribe en silencio, aplicando
el mismo principio de "Operational Truth" del resto del sistema al chat).
Se persiste: rol, contenido visible, `tool_calls` solicitados, `tool_name`/
`tool_result` (minimizado, nunca la fila cruda de BD ni el payload upstream
completo), `provenance`, modelo usado, tokens de entrada/salida, timestamps.
**Nunca se persiste**: la API key, ningún secreto, ni un "chain of thought"
interno del modelo (sólo su contenido final visible). Los `JSONField` usan
`DjangoJSONEncoder` — un resultado de tool real trae `Decimal`/`date`
(GWP, fechas de vigencia), que el encoder JSON estándar no serializa; esto
se encontró y corrigió durante el smoke real (ver 04_VERIFICATION.md).

## Control de costos

`enforce_cost_controls` (llamado al inicio de cada turno) aplica
`AI_MAX_MESSAGES_PER_CONVERSATION` (por conversación) y
`AI_MAX_REQUESTS_PER_ORG_PER_HOUR` (contando mensajes `assistant` de la
última hora para toda la organización — sin tabla nueva, derivado de
`Message` ya persistido, mismo espíritu "derive, don't duplicate" ya usado
en SOURCE-WATCH/EC3). El historial enviado al modelo está acotado a 20
mensajes. `AI_MAX_TOOL_ITERATIONS` evita que un turno encadene tools sin
límite. Nada de esto requiere una tabla de rate-limit nueva.

## Seed de demostración

`python manage.py seed_ai_demo_tenant [--reset]` — ver
`docs/ai/05_SEED_AND_DEMO.md`.

## Troubleshooting

| Síntoma | Causa | Acción |
|---|---|---|
| El chat responde "no está habilitado" sin llamar al proveedor | `OPENROUTER_ENABLED=false` o `OPENROUTER_API_KEY`/`OPENROUTER_MODEL` vacíos | Configurar las 4 variables en el `.env` de **raíz** (no `backend/.env`) |
| `get_ec3_opportunities`/`get_ec3_mapping_status` siempre muestran `STALE`/`ec3_disabled` en el tenant demo | Comportamiento correcto: EC3 requiere su propia configuración (`EC3_ENABLED`, derechos) independiente de este chat | Configurar `EC3_ENABLED=true` (ver `docs/integrations/ec3/03_OPERATIONS.md`) para ver el estado `MAPPED` |
| Un turno tarda el máximo de iteraciones y responde "no pude completar la consulta" | El modelo encadenó tools sin llegar a una respuesta final antes de `AI_MAX_TOOL_ITERATIONS` | Reformular la pregunta de forma más específica, o subir el límite si el caso de uso lo justifica |
| 401 en cualquier endpoint `/api/ai/...` | Sesión no autenticada — el middleware de tenant intercepta antes que la vista | Iniciar sesión real (`force_login`/cookies), no `force_authenticate` en tests |
| 404 en `/api/ai/<organizacion_id>/...` | El usuario no tiene membresía activa en esa organización, o la organización no existe | Verificar `UsuarioOrganizacion` — el 404 es deliberado (nunca revela si el tenant existe) |
