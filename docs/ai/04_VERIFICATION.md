# AI-INTELLIGENCE-01 — Verificación

## Suite de pruebas (`apps/ai/tests/`)

56 pruebas, todas en verde, mockeando siempre OpenRouter (nunca red real
en la suite automática):

| Archivo | Cubre |
|---|---|
| `test_providers.py` | Proveedor OpenRouter: disponibilidad, timeout/red, 401→auth, 429→rate limit, respuesta vacía, argumentos de tool malformados, modelo configurable, la API key nunca aparece en un error |
| `test_system_prompt.py` | Versión, frases de guardrail obligatorias, "nunca consulta la BD directamente" |
| `test_tools.py` | Aislamiento de tenant, RBAC, argumentos faltantes, tool desconocida, esquemas OpenAI válidos, búsqueda real en la base de conocimiento |
| `test_orchestrator.py` | Respuesta simple, tool-call + respuesta final + provenance, fallo de tool reportado (nunca oculto/inventado), límite de iteraciones (nunca bucle infinito), proveedor deshabilitado, error de proveedor, historial reenviado, límites de conversación/hora, **serialización Decimal/date en tool_result** |
| `test_greeting.py` | Saludo automático sin llamar al proveedor, idempotente, no se reemite tras iniciar conversación real |
| `test_views.py` | Auth, aislamiento cross-tenant, saludo vía API, envío de mensaje, validación de contenido vacío, listado propio |
| `test_tenant_isolation.py` | Un LLM pidiendo `material_id` de otro tenant nunca lo obtiene; conversación de un tenant invisible desde otro; `obra` de otra organización rechazada |
| `test_seed_command.py` | Idempotencia del seed, `--reset` conserva la organización |

## Smoke real (OpenRouter, 2026-09-12)

`OPENROUTER_API_KEY` disponible en `backend/.env` (no cargado por Django
por defecto — ver 03_OPERATIONS.md). Se inyectó como variable de entorno
de proceso para el smoke, junto con `OPENROUTER_MODEL=google/gemini-2.5-flash`
(elegido por ser el mismo modelo ya usado con éxito por
`DOCUMENT_AI_PROVIDER=openrouter` en este mismo proyecto — nunca un modelo
inventado). Nunca se imprimió la key.

1. **Conexión y modelo** — confirmado (`provider.available=True`,
   `OPENROUTER_MODEL` real).
2. **Pregunta simple** ("Hola, ¿quién eres y qué puedes hacer?") — 1344
   tokens de entrada, 404 de salida, respuesta coherente sin ninguna tool.
3. **Tool call real** ("¿Cuál es el material con mayor hotspot...?") —
   primer intento generó una pregunta de aclaración (comportamiento
   razonable, no un fallo); en el turno siguiente el modelo llamó
   `get_material_hotspots` realmente y respondió: *"El material con mayor
   hotspot... es HORIZONTE-HORMIGON, con un impacto de 460800.00 kgCO2e,
   lo que representa el 93.79%..."* — coincide exactamente con el dato
   real sembrado por `seed_ai_demo_tenant`.
4. **Encontró un bug real**: el primer intento de un tool-call real
   falló al persistir — `Message.tool_result` usaba el encoder JSON
   estándar, que no serializa `Decimal`/`date` (valores reales que
   `material_hotspots`/otros servicios sí devuelven). Corregido con
   `DjangoJSONEncoder` en los tres `JSONField` de `Message`
   (`tool_calls`, `tool_result`, `provenance`), migración
   `0002_alter_message_provenance_alter_message_tool_calls_and_more`.
   Regresión agregada en `test_orchestrator.py`. Ninguna prueba mockeada
   había encontrado esto porque los resultados de tool falsos en esas
   pruebas nunca incluían un `Decimal` real — exactamente el tipo de
   brecha que un smoke real está para encontrar.
5. Tras el fix, el flujo completo (pregunta → tool real → respuesta final
   con provenance) se repitió con éxito.

## Frontend

`npm run build` exitoso (sin errores nuevos; sólo advertencias
preexistentes de tamaño de chunk, no relacionadas). `npx eslint` limpio
sobre los archivos nuevos.

**Verificación interactiva completa en navegador real**: el puerto 8000
resultó estar ocupado por otro proceso en este entorno (confirmado con un
bind de socket directo — no un bloqueo de permisos); se sirvió el backend
en el puerto 8010 y se habilitó temporalmente ese origen más la cabecera
CORS personalizada `x-organization-id` sólo para la duración de la
prueba (revertido por completo inmediatamente después, confirmado con
`git diff` limpio). Con eso:

1. Login real con el usuario admin del tenant demo (contraseña temporal,
   revertida a `set_unusable_password()` al terminar).
2. Botón flotante "Carbono Zero Intelligence" visible en toda página
   autenticada; al abrirlo, resumió correctamente la conversación ya
   creada por el smoke real por script — **conversación persistente
   confirmada entre una sesión de script y una sesión de navegador real**.
3. Envío de un mensaje nuevo en vivo ("¿Esta obra cumple con la normativa
   ambiental?"): el modelo real respondió rechazando declarar
   cumplimiento y explicando el límite de su función — el guardrail
   crítico de la pregunta 14 de la matriz de demostración, confirmado en
   la interfaz real, no sólo en un test o un script.

## Gates

- `manage.py check`: sin incidencias (con `apps.ai` incluida).
- `makemigrations --check --dry-run`: sin cambios pendientes.
- `git diff --check`: correcto.
- Regresión completa `apps.analytics apps.knowledge apps.iot apps.ec3 apps.ai`:
  **1514 tests, 27 errores** — exactamente el baseline histórico de 27
  errores preexistentes (documentados desde SOURCE-WATCH-01: 20 en
  `test_professional_v2`, 7 en `test_generated_emissions_indicator`),
  verificados nombre por nombre. Cero fallas nuevas. Suite `apps.ai`
  aislada: 56/56 OK.
- Cero secretos: `.env.example` documenta las variables `OPENROUTER_*`/`AI_*`
  sin valores; ningún archivo de `apps/ai/` contiene un valor real de
  `OPENROUTER_API_KEY`; la key nunca se imprimió durante el smoke real.
