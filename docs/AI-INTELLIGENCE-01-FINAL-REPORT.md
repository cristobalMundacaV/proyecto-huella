# AI-INTELLIGENCE-01 — Informe final de macrofase

Verdict: **DONE**

No se realizó commit ni push (no autorizado para esta macrofase). Todos los
cambios permanecen en el árbol de trabajo local.

## 1. Objetivo

Chat profesional de inteligencia ambiental dentro de Carbono Zero,
conectado a las capas reales del sistema (tenant, obras, materiales,
indicadores, MATERIAL-INTELLIGENCE, EC3/openEPD, SOURCE-WATCH/knowledge,
provenance, calidad, alertas, cálculos históricos, oportunidad) mediante
tool-calling controlado por el backend — el LLM nunca consulta la base de
datos directamente ni inventa un resultado que una tool no entregó.

## 2. Auditoría previa (paso 0)

Ver `docs/ai/01_ARCHITECTURE_DISCOVERY.md`. Hallazgos que evitaron
duplicar capas: patrón de proveedor abstracto ya existente
(`EnvironmentalAgentProvider`/`OpenAIEnvironmentalProvider`, de una sola
pasada, sin tools — se construyó una interfaz nueva y mínima
`AIProvider`/`OpenRouterProvider` para el caso conversacional, que sí
necesita historial y function-calling); patrón real de llamada a
OpenRouter ya en uso (`openrouter_document_provider.py`); gobernanza de
autoridad IA ya establecida (`IntelligenceOperation`/`AI_AUTHORITY`,
reutilizada tal cual); `ContextGateway` como la capa de "tools" que ya
existía en espíritu; RBAC/tenant (`require_tenant_permission`,
`organization_available_to_user`, `work_for_organization`) reutilizados
sin ningún mecanismo paralelo.

## 3. Arquitectura final

```
Usuario → apps.ai.views (auth + tenant + RBAC)
  → orchestrator.run_turn (persiste turno, aplica cost controls)
  → system_prompt.build_messages
  → providers.OpenRouterProvider.chat(messages, tools=14 esquemas)
  → si el modelo pide tool(s): tools.execute_tool (tenant-checked, RBAC-checked, solo lectura)
  → resultado estructurado se persiste y se reenvía al modelo
  → respuesta final se persiste con provenance
```

## 4. Archivos creados/modificados

**Backend (`backend/apps/ai/`, nuevo)**: `apps.py`, `models.py`
(`Conversation`, `Message` — append-only), `providers.py`
(`AIProvider`/`OpenRouterProvider`), `tools.py` (14 tools), `system_prompt.py`,
`orchestrator.py`, `greeting.py`, `views.py`, `urls.py`,
`management/commands/seed_ai_demo_tenant.py`, migraciones `0001_initial`,
`0002_alter_message_provenance_alter_message_tool_calls_and_more` (fix
`DjangoJSONEncoder`), `tests/` (8 archivos, 56 pruebas).

**Backend modificado**: `config/settings.py` (`apps.ai` en
`INSTALLED_APPS`, variables `OPENROUTER_*`/`AI_*`), `config/urls.py`
(`api/ai/`), `apps/analytics/permissions.py` (`Permission.
INTELLIGENCE_CHAT_VIEW`, incluido en `VIEW_PERMISSIONS`).

**Frontend (nuevo)**: `frontend/src/features/ai-chat/` — `services/
aiChatApi.js`, `components/AiChatPanel.jsx`, `components/AiChatLauncher.jsx`.
**Frontend modificado**: `AuthenticatedLayout.jsx` (monta el launcher
flotante en toda página autenticada), `package.json`/`package-lock.json`
(`react-markdown`, `remark-gfm`).

**Documentación (nueva)**: `docs/ai/01_ARCHITECTURE_DISCOVERY.md`,
`02_DEMO_QUESTIONS_AND_EXPECTED_BEHAVIOR.md` (20 preguntas),
`03_OPERATIONS.md`, `04_VERIFICATION.md`, `05_SEED_AND_DEMO.md`.

Ningún archivo de `apps/knowledge/`, `apps/ec3/` (salvo lectura) ni del
"Copiloto" existente (`features/intelligence/`) fue modificado — son
dominios distintos, coexisten sin fusionarse.

## 5. Modelos y migraciones

`Conversation` (organización + usuario + obra opcional, nunca
reasignables) y `Message` (append-only: `save()`/`delete()` lanzan
`ValidationError` sobre una fila ya creada). Dos migraciones: la inicial,
y una segunda que cambia el encoder de los `JSONField` a
`DjangoJSONEncoder` — necesaria porque un resultado de tool real trae
`Decimal`/`date` (encontrado por el smoke real, ver sección 9). `manage.py
makemigrations --check --dry-run`: sin cambios pendientes.

## 6. Endpoints internos

`GET,POST /api/ai/<organizacion_id>/conversations/`, `GET /api/ai/
<organizacion_id>/conversations/<id>/`, `POST /api/ai/<organizacion_id>/
conversations/<id>/messages/`. Protegidos por `OrganizacionTenantMiddleware`
ya existente (401 sin auth, 404 sin membresía) más `Permission.
INTELLIGENCE_CHAT_VIEW` explícito en la vista.

## 7. Tools implementadas (14/14, todas de solo lectura)

`get_current_organization`, `list_projects`, `get_project_summary`,
`get_environmental_indicators`, `get_emissions_summary`,
`get_material_summary`, `get_material_hotspots`, `get_evidence_quality`,
`get_open_alerts`, `get_ec3_mapping_status`, `get_ec3_opportunities`,
`get_factor_provenance`, `get_historical_trends`,
`search_environmental_knowledge` — cada una un adaptador delgado sobre un
servicio ya existente (ver tabla completa en `docs/ai/03_OPERATIONS.md`),
nunca una reimplementación. Cada tool re-verifica tenant y el permiso RBAC
más específico de su dominio antes de tocar cualquier dato.

## 8. Guardrails

Solo lectura por diseño (ninguna tool escribe). El system prompt exige:
nunca inventar métricas/factores/cumplimiento/evidencia; nunca presentar
un candidato EC3 como aprobado si no está `MAPPED`; nunca presentar una
oportunidad como decisión constructiva; explicitar cuando falta
información; distinguir hechos/inferencias/recomendaciones; explicar
provenance; advertir calidad de datos insuficiente. Verificado en vivo
(sección 9): la pregunta "¿Esta obra cumple con la normativa ambiental?"
fue respondida correctamente rechazando declarar cumplimiento.

## 9. Smoke real (OpenRouter + demo tenant, 2026-09-12)

`OPENROUTER_API_KEY` disponible en `backend/.env` (no cargado por Django
por defecto — mismo patrón que `EC3_API_TOKEN`, documentado). Inyectado
como variable de entorno de proceso, nunca impreso, nunca escrito a un
archivo del repositorio. Modelo usado: `google/gemini-2.5-flash` (ya
probado con éxito en este proyecto vía `DOCUMENT_AI_PROVIDER=openrouter`).

- Conexión y modelo: confirmados.
- Pregunta simple: respuesta coherente, sin tool, tokens reales contados.
- Pregunta con tool real: el modelo llamó `get_material_hotspots` de
  verdad y respondió citando el dato real sembrado
  ("HORIZONTE-HORMIGON, 460800.00 kgCO2e, 93.79%").
- **Encontró un bug real**: `Message.tool_result` no serializaba
  `Decimal`/`date` (valores reales que las tools sí devuelven) — corregido
  con `DjangoJSONEncoder` + migración + prueba de regresión. Ninguna
  prueba mockeada lo había detectado: exactamente el tipo de brecha que
  un smoke real existe para encontrar.
- Verificación interactiva completa en navegador: login real con el
  admin del tenant demo, panel de chat abierto desde el botón flotante,
  conversación previa (creada por el smoke por script) visible y
  persistida correctamente, envío de un mensaje nuevo en vivo
  ("¿Esta obra cumple con la normativa ambiental?") con respuesta real
  del modelo rechazando declarar cumplimiento — el guardrail crítico de
  la pregunta 14 de la matriz de demostración, verificado en vivo, no
  sólo en un test.
- Contratiempos de entorno resueltos durante la verificación: el puerto
  8000 estaba ocupado por otro proceso en este entorno (no un bloqueo de
  permisos, diagnosticado con un bind de socket directo); se usó el
  puerto 8010 para el backend y se permitió temporalmente ese origen y
  la cabecera `x-organization-id` en CORS sólo para la duración de la
  prueba — **revertido por completo** inmediatamente después (confirmado
  con `git diff` limpio sobre `settings.py` salvo los cambios legítimos
  de esta macrofase). La contraseña temporal puesta al admin demo para
  poder iniciar sesión también se revirtió a `set_unusable_password()`.

## 10. Frontend

`Carbono Zero Intelligence`: botón flotante en toda página autenticada
(`AiChatLauncher`, oculto si el usuario no tiene `intelligence_chat.view`
o no hay organización activa) que abre un panel lateral (`AiChatPanel`)
construido sobre las variables CSS y componentes ya existentes
(`Button`, patrón de `Drawer`), con saludo automático, mensajes usuario/
asistente, markdown seguro (`react-markdown` + `remark-gfm`, sin HTML
crudo; enlaces con esquema no seguro se renderizan como texto plano),
sección "Fuentes utilizadas" colapsable, estado de escritura, manejo de
errores con reintento, sugerencias iniciales de preguntas, envío con
Enter/Shift+Enter, contexto de organización activa vía
`useOrganizacionActiva`. No se tocó ni fusionó con el "Copiloto" existente
(`features/intelligence/`) — dominio distinto (propuestas de una sola
pasada vs. conversación libre), coexisten. `npm run build`/`eslint`
limpios; **verificado también de forma interactiva en navegador real**
(sección 9) — no sólo build+lint estáticos.

## 11. Tenant isolation y RBAC

Cero mecanismo nuevo: reutiliza `OrganizacionTenantMiddleware`,
`organization_available_to_user`, `require_tenant_permission`,
`work_for_organization` tal cual. Permiso nuevo mínimo
`Permission.INTELLIGENCE_CHAT_VIEW`, incluido en `VIEW_PERMISSIONS` (todos
los roles lo heredan, igual que cualquier otro permiso de lectura).
Pruebas explícitas cross-tenant en `test_tenant_isolation.py`, incluyendo
un LLM simulado pidiendo un `material_id` de otra organización — la tool
lo rechaza (`not_found`) sin excepción y sin filtrar dato alguno.

## 12. Cost controls

`AI_MAX_MESSAGES_PER_CONVERSATION`, `AI_MAX_REQUESTS_PER_ORG_PER_HOUR`
(derivado de `Message` ya persistido, sin tabla de rate-limit nueva),
`AI_MAX_TOOL_ITERATIONS` (nunca un bucle infinito de tool-calls), historial
enviado al modelo acotado a 20 mensajes, `AI_MAX_OUTPUT_TOKENS`/
`AI_TEMPERATURE` configurables, modelo configurable sin default hardcodeado.

## 13. Seed de demostración

`python manage.py seed_ai_demo_tenant [--reset]` — "Constructora
Horizonte Demo SpA" (`DEMO_HORIZONTE`), 100% sintética. Ver
`docs/ai/05_SEED_AND_DEMO.md` para el detalle completo: 2 obras, 6
materiales (uno de ellos con mapping EC3 real y gobernado + una
oportunidad EC3 potencial comparable), 4 meses de historial calculado con
el motor real, 1 hotspot real (~93.8%), 1 alerta abierta, un indicador sin
historial y un mes de agua sin observación (casos deliberados de "no
invención"). Idempotente, probado en `test_seed_command.py`.

## 14. Matriz de preguntas de demostración

`docs/ai/02_DEMO_QUESTIONS_AND_EXPECTED_BEHAVIOR.md` — 20 preguntas con
tools esperadas, datos esperados, comportamiento esperado y señales de
fallo. Las preguntas 14 (cumplimiento), 15 (aprobación automática) y 16
(cross-tenant) están marcadas como casos críticos; la 14 se verificó en
vivo contra el modelo real (sección 9).

## 15. Tests

56 pruebas en `apps/ai/tests/`, todas en verde (proveedor OpenRouter
mockeado en la suite automática; nunca red real). Cobertura: proveedor
(auth, timeout, 429, respuesta inválida, modelo configurable, proveedor
deshabilitado, la key nunca aparece en un error), orquestación (tool
real, fallo de tool no oculto/inventado, límite de iteraciones, historial,
límites de costo, serialización Decimal/date), tenant isolation, RBAC,
saludo inicial, system prompt, vistas API, seed idempotente. Ver detalle
en `docs/ai/04_VERIFICATION.md`.

## 16. Gates

- `manage.py check`: sin incidencias.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- `git diff --check`: correcto (sólo advertencias CRLF benignas, mismo
  patrón preexistente del repositorio).
- **Regresión completa `apps.analytics apps.knowledge apps.iot apps.ec3 apps.ai`:
  1514 tests, 27 errores — exactamente los 27 conocidos y ya documentados
  desde SOURCE-WATCH-01 (20 en `test_professional_v2`, 7 en
  `test_generated_emissions_indicator`), verificados nombre por nombre
  contra el log. Cero fallas nuevas, cero relación con AI-INTELLIGENCE-01.**
  Suite `apps.ai` aislada: 56/56 OK.
- Cero secretos: confirmado por inspección de diff (`.env.example` sin
  valores, ningún archivo de `apps/ai/` con el valor real de
  `OPENROUTER_API_KEY`, la key nunca impresa durante el smoke real, la
  contraseña temporal del admin demo revertida a `set_unusable_password()`,
  el override temporal de CORS revertido por completo — confirmado con
  `git diff` limpio sobre `settings.py`).

## 17. Deuda técnica real restante

- No existe streaming de respuesta (mensaje completo de una vez) — no
  pedido explícitamente por la misión, aceptable para esta fase.
- El chat no ofrece selección explícita de obra en la UI (el backend sí
  acepta `obra_id` en la creación de conversación); las preguntas que
  requieren precisar una obra dependen de que el propio modelo pregunte
  — comportamiento observado y correcto en el smoke real, pero una mejora
  de UX futura sería exponer un selector de obra en el panel.
- El estado EC3 del tenant demo depende de `EC3_ENABLED`/derechos
  configurados igual que en producción (correcto, no un defecto) — sin
  esa configuración, el material de hormigón se reporta `STALE` en vez de
  `MAPPED`; documentado explícitamente para no confundirlo con un bug.
- Sin pruebas automatizadas de frontend para el panel de chat (el resto
  del frontend tampoco tiene cobertura de test por feature de forma
  sistemática); verificado en su lugar con build de producción limpio,
  lint limpio y una verificación interactiva completa en navegador real.

## 18. Verdict final

**DONE.**

Las 16 secciones de la misión están completas: proveedor OpenRouter
funcional (con smoke real exitoso que encontró y corrigió un bug real),
chat frontend funcional (verificado con build, lint y una sesión
interactiva completa en navegador real — login, panel abierto,
conversación persistida, mensaje nuevo enviado y respondido en vivo por
el modelo real), saludo automático, conversación persistente, tool
orchestration con 14 herramientas de solo lectura, tenant isolation y
RBAC reutilizando la infraestructura existente sin mecanismo paralelo,
provenance, guardrails verificados en vivo (incluida la pregunta crítica
de cumplimiento normativo), control de costos, seed de demostración
idempotente con todos los escenarios requeridos, matriz de 20 preguntas,
56/56 pruebas automatizadas en verde, documentación completa bajo
`docs/ai/`. `manage.py check` limpio, migraciones limpias, cero secretos,
cero regresiones nuevas sobre 1514 pruebas totales del sistema. No se
realizó commit ni push, conforme a la instrucción explícita de esta
macrofase.
