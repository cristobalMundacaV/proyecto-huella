# AI-INTELLIGENCE-01 — Auditoría de arquitectura (paso 0)

Auditoría previa a programar, per mandato de la misión. Todo lo listado aquí
fue verificado leyendo el código real, no inferido.

## 1. Integración LLM ya existente (no duplicar)

`openai==2.32.0` ya está en `backend/requirements.txt` y en uso real, todo en
`apps/analytics/services/`:

| Archivo | Qué hace |
|---|---|
| `ai_advisor.py` | `generar_analisis_ia(payload)` — prompt único a OpenAI `gpt-5-mini` vía `.responses.create`, retorna texto. Usado por `POST /api/ai-advisor/`. |
| `environmental_agent.py` | **Patrón de proveedor abstracto ya establecido**: `EnvironmentalAgentProvider` (base, `name`/`model`/`generate(*, system_rules, context)`) → `OpenAIEnvironmentalProvider`. `EnvironmentalAgentService.recommend(problem)` arma contexto acotado, llama al proveedor, valida el JSON devuelto, persiste `RecomendacionAgenteAmbiental`. |
| `copilot_v2.py` | `CopilotProposalService` — reutiliza `OpenAIEnvironmentalProvider` + `ContextGateway`, produce propuestas para revisión humana, escribe auditoría en `HitoDecisionIA`. |
| `material_intelligence_copilot.py` | Copiloto explicativo sobre hallazgos ya deterministas de MATERIAL-INTELLIGENCE — nunca decide, sólo explica. |
| `document_provider_registry.py` / `openrouter_document_provider.py` / `openai_document_provider.py` | Extracción visual de documentos, proveedor seleccionable por `DOCUMENT_AI_PROVIDER`. **`openrouter_document_provider.py` es la referencia real de cómo este repo ya llama a OpenRouter**: `OpenAI(api_key=..., base_url="https://openrouter.ai/api/v1").chat.completions.create(...)`, con manejo explícito de `APIConnectionError`/`APIStatusError`/timeout y nunca exponer el cuerpo/credenciales en errores. |

**Ninguno de estos es conversacional ni usa tool/function calling.** Todos son
de una sola pasada (prompt → JSON/texto). Ese es exactamente el vacío que
cierra AI-INTELLIGENCE-01 — no hay nada que duplicar aquí, sólo un patrón de
proveedor y de manejo de errores que replicar para el caso conversacional.

Modelos de apoyo ya existentes (`apps/analytics/models/intelligence.py`):
`RecomendacionAgenteAmbiental`, `MemoriaOrganizacion`, `RestriccionContextual`,
`HitoDecisionIA` — pertenecen al dominio "Copiloto de problemáticas", no al
chat conversacional; **no se reutilizan como modelos de conversación** (dominio
distinto: propuestas estructuradas sobre una `ProblematicaAmbiental` vs.
conversación libre multi-turno). Se crean modelos nuevos, acotados a `apps.ai`.

Gobernanza de autoridad IA ya existente y **reutilizada tal cual**:
`apps/analytics/policies/intelligence.py` — `IntelligenceOperation` (enum) +
`AI_AUTHORITY` (dict) + `validate_ai_operation(operation)`. Como este chat es
enteramente de sólo lectura, cada turno de orquestación llama
`validate_ai_operation(IntelligenceOperation.READ_CONTEXT)` antes de ejecutar
cualquier tool — sin inventar un mecanismo de guardrail paralelo.

## 2. Tenant / organización / RBAC (reutilizado tal cual, sin nuevo mecanismo)

- **Modelo**: `Organizacion` (`apps/analytics/models/platform.py`), clave
  natural `organizacion_id`.
- **Membresía**: `UsuarioOrganizacion` (`rol`, `alcance` organizacion/obras),
  `UsuarioObraAcceso` para acceso granular a obras específicas.
- **Resolución de tenant**: no hay `request.organization` de middleware ni
  selección por sesión/header. Cada vista resuelve explícitamente vía
  `apps.analytics.selectors.environmental_flows.organization_available_to_user(user, organizacion_id)`
  a partir de un segmento de URL. El middleware
  `OrganizacionTenantMiddleware` (`apps/analytics/tenant.py`) sólo protege
  vistas con `organizacion_id` en la URL y devuelve **404** (no 403) si el
  usuario no tiene membresía activa — nunca revela que el tenant existe.
- **RBAC**: `apps/analytics/permissions.py` — `Permission` (~45 constantes),
  `ROLE_PERMISSIONS` por rol (`ADMIN` = todos; el resto = `VIEW_PERMISSIONS`
  base + extras), `require_tenant_permission(user, organization, permission)`
  (levanta `PermissionDenied`), `has_tenant_permission`, `filter_works_for_user`/
  `user_can_access_work`/`require_work_access` para acotar por obra cuando
  `alcance == OBRAS`.
- **Obra en contexto**: no existe una "obra actual" persistente. Cada
  operación que la necesita la recibe explícita (`obra_id`) y la resuelve vía
  `work_for_organization(organization, work_id)` — igual patrón se usa aquí:
  cada tool que opera sobre una obra recibe `obra_id` como argumento explícito
  del LLM, nunca un "contexto ambiental" implícito de sesión.
- **Patrón estándar en toda vista mutante/lectora sensible**: autenticar →
  resolver organización → `require_tenant_permission` → (si aplica) resolver
  obra/recurso y validar pertenencia → ejecutar.

Se añaden dos constantes nuevas a `Permission`
(`INTELLIGENCE_CHAT_USE`) e integran a `ROLE_PERMISSIONS` (todos los roles
salvo el más restringido tienen acceso de lectura; ver
`docs/ai/05_TENANT_ISOLATION_AND_RBAC.md`) — no se crea un sistema de permisos
paralelo.

## 3. `ContextGateway` — la capa de "tools" ya existe parcialmente

`apps/analytics/services/context_gateway.py` es, en la práctica, exactamente
la forma que debía tener una capa de tools: una clase con métodos acotados
(`MAX_HISTORY=10`, `MAX_SERIES=12`, `MAX_MEMORY=20`), cada uno empieza con
`self._tenant(instance, organization)` (compara `organizacion_id`), y devuelve
un dict `{"context_type": ..., "references": {...}, ...datos...}`. Métodos
relevantes que las tools de AI-INTELLIGENCE-01 **reutilizan directamente**
en lugar de reconstruir su propia agregación:

- `work(work, organization)` → `construction_v1.work_context(work)`.
- `indicator_history(indicator, organization)` → serie de `ValorIndicador`.
- `evidence(evidence, organization)` → estado documental + versiones,
  excluye contenido pesado (`archivo`, `texto_extraido`).
- `material_intelligence(material, organization, *, work=None)` → evidencia,
  suitability, functional use, cadena de comparabilidad — nunca calcula nada,
  sólo proyecta hallazgos ya deterministas de MATERIAL-INTELLIGENCE.

Servicios de dominio adicionales que las tools envuelven (nunca reimplementan):

| Servicio | Uso en una tool |
|---|---|
| `material_hotspots.material_hotspots(organization, work=, start=, end=, categoria=, standard=)` | `get_material_hotspots` |
| `material_opportunities.detect_opportunities(organization, work=, ...)` | parte de `get_ec3_opportunities` (alternativas ya mapeadas/activas) |
| `material_ledger.material_ledger_totals(organization, work=, start=, end=, categoria=, standard=)` | `get_emissions_summary` |
| `material_ledger.ledger_entry_provenance(calculo)` | `get_factor_provenance` |
| `material_quality.assess_factor_data_quality(factor)` / `assess_material_data_quality(candidate)` | `get_evidence_quality` |
| `apps.ec3.opportunity.material_candidate_opportunities` / `compare_candidates` | parte de `get_ec3_opportunities` (candidatos EC3 aún no aplicados) |
| `apps.ec3.services.candidate_data` / `provenance` | `get_ec3_mapping_status` |
| `apps.knowledge.source_health.source_health` / `apps.knowledge.review_queue` | insumo de `search_environmental_knowledge` y `get_open_alerts` |
| `ProblematicaAmbiental` (estado ≠ cerrada/resuelta) | `get_open_alerts` (el "alerta" moderno; `AlertaCumplimientoAmbiental` es legacy, `apps/analytics/models/legacy.py`, **no se usa** para capacidades nuevas) |

No se usa `RegistroEmision`/`FactorEmision`/`AlertaCumplimientoAmbiental`
(legacy) para ninguna tool nueva — sólo el stack v2 (`ActividadOperacional`,
`MaterialOperacional`, `CalculoAmbiental`, `MaterialFactorMapping`,
`IndicadorAmbiental` v2, `ProblematicaAmbiental`).

## 4. Convención de nueva app Django

Confirmado idéntico entre `apps.ec3` y `apps.knowledge`:
`INSTALLED_APPS` → `"apps.ai.apps.AiConfig"`; `apps/ai/apps.py` con
`AppConfig`/`ready()`; `apps/ai/urls.py` con `path()` + `@api_view`
(sin DRF routers/viewsets en todo el repo); una línea nueva en
`config/urls.py` (`path("api/ai/", include("apps.ai.urls"))`).

## 5. Discrepancia real de configuración encontrada (documentada, no "arreglada" en silencio)

- `config/settings.py` carga **sólo** `load_dotenv(PROJECT_ROOT / ".env")`
  (raíz del repo). `docker-compose.yml` también monta el `.env` de raíz.
- `backend/.env` (un archivo *distinto*, también gitignorado) contiene
  `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_ENABLED=true` y
  `OPENROUTER_MODEL=` (vacío) — **pero Django nunca lo lee**. Es el mismo
  patrón exacto ya encontrado y documentado durante el smoke real de EC3
  (`EC3_API_TOKEN` estaba en `backend/.env`, no en el `.env` de raíz).
- `config/settings.py` ya define `OPENAI_API_KEY` y `OPENROUTER_API_KEY`
  (usados hoy sólo por `DOCUMENT_AI_PROVIDER=openrouter`); en el `.env` de
  raíz real, ambos están vacíos actualmente.
- **Consecuencia para esta macrofase**: se añaden `OPENROUTER_ENABLED`,
  `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL` (y las variables `AI_*` de esta
  macrofase) a `config/settings.py` y a `.env.example` (raíz), documentando
  claramente que deben vivir en el `.env` de raíz para tener efecto. Para el
  smoke real (paso 12 de la misión) se inyectan como variables de entorno de
  proceso a partir del valor ya presente en `backend/.env`, exactamente como
  se hizo para `EC3_API_TOKEN` — sin copiar el secreto a ningún archivo del
  repositorio.

## 6. Frontend

React 19 + Vite + Tailwind v4 (sin TypeScript). Patrones a reutilizar:

- `frontend/src/shared/ui/` (barrel `index.js`): `Button`, `Drawer` (panel
  lateral deslizante, ya con focus-trap/Escape — base natural del chat),
  `Modal`, `Alert`/`EmptyState`/`ErrorState`/`LoadingState`, `Textarea`.
- `frontend/src/shared/services/api.js`: cliente axios único, sesión/cookie +
  CSRF (no bearer tokens), `humanizeApiError` para errores legibles.
- Contexto de tenant/obra: `useOrganizacionActiva()`
  (`features/organizaciones/context/OrganizacionActivaContext.jsx`),
  `useOperationalWorkspace()` (`features/workspace/context/
  OperationalWorkspaceContext.jsx`), `useAuth()`. Toda llamada del chat al
  backend viaja con `activeOrganizacionId` (y `obra_id` cuando corresponda)
  tomados de estos contextos — nunca un ID libre del usuario.
- RBAC en frontend: `usePermissions().can(permission)`
  (`features/auth/hooks/usePermissions.js`).
- **No existe** chat-bubble/message-list en ningún lugar del frontend. Existe
  un "Copiloto" (`frontend/src/features/intelligence/pages/CopilotPage.jsx`)
  de una sola pasada (formulario → propuesta estructurada con confirmación
  humana) — **dominio distinto, no se toca ni se fusiona**. El nuevo chat
  vive en una feature separada (`frontend/src/features/ai-chat/`) con su
  propio punto de entrada, evitando confundir ambas superficies.
- No hay librería de markdown ni modo oscuro realmente conmutable (el CSS de
  `theme.css` para `[data-theme="dark"]` existe pero nada lo activa) — se
  añade `react-markdown` + `remark-gfm` (con saneamiento) y el chat se
  construye sólo con las variables CSS existentes (hereda modo oscuro
  automáticamente el día que alguien active el toggle, sin trabajo extra).

## 7. Seeds existentes — patrón a seguir, no el contenido

Los seeds existentes (`seed_demo_carbono_zero.py`,
`seed_construccion_demo.py`, `seed_construccion_historica.py`) usan en su
mayoría el stack **legacy** (`RegistroEmision`, `EtapaObra`,
`AlertaCumplimientoAmbiental`). El patrón idempotente que sí se reutiliza:
`Organizacion.objects.update_or_create(organizacion_id=<id fijo>, defaults={...})`
con un prefijo reconocible. El nuevo comando `seed_ai_demo_tenant` construye
datos exclusivamente sobre el stack **v2 moderno** (idéntico al usado en
`apps/ec3/tests/test_governance.py`: `Organizacion` → `MaterialOperacional` →
`Obra`/`ActividadOperacional`/`Observacion`/`EventoMaterial` →
`calculate_activity` → `MaterialFactorMapping` vía `propose_material_mapping`/
`approve_material_mapping` → `IndicadorAmbiental` v2 → `ProblematicaAmbiental`
→ candidato EC3 mapeado), nunca los modelos legacy.

## 8. Conclusión de diseño

- **Proveedor**: interfaz nueva y mínima `AIProvider` (no la de
  `environmental_agent.py`, que es de una sola pasada sin tools) →
  `OpenRouterProvider`, siguiendo el patrón de llamada/errores de
  `openrouter_document_provider.py`.
- **Tools**: funciones nuevas en `apps/ai/tools.py` que son adaptadores
  delgados sobre los servicios de la sección 3 — nunca acceso directo a
  modelos fuera de lo que esos servicios ya exponen, siempre con
  `require_tenant_permission` + verificación de pertenencia al tenant.
- **Orquestador**: nuevo, en `apps/ai/orchestrator.py` — no existe nada
  parecido a reutilizar (todo lo existente es de una sola pasada).
- **Modelos de conversación**: nuevos (`Conversation`, `Message`) en
  `apps/ai/models.py` — dominio distinto de `HitoDecisionIA`/
  `RecomendacionAgenteAmbiental`.
- **RBAC/tenant**: cero mecanismo nuevo — se reutiliza
  `require_tenant_permission`/`organization_available_to_user`/
  `work_for_organization` tal cual.
