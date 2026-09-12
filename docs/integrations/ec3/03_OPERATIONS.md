# EC3-01 — Operación y contrato interno

## Alcance

Integración backend dirigida a EPDs públicas mediante openEPD. No descarga masiva,
no ingestión de PDFs, no frontend con credenciales, no selección automática de EPD.
El registro de fuente pertenece a Knowledge Hub; los facts, candidatos, cache y
decisiones EC3 viven en `apps.ec3`. EC3 conserva su autoridad sobre el dato.

## Contrato upstream verificado

Se obtuvo el OpenAPI publicado por el explorador oficial el 2026-09-12. Hash del
documento original:
`ad66c6a1d33af653dac426117186060db0395bbc3a94e310d49dc1f28570339c`.
El extracto reproducible está en [02_OFFICIAL_CONTRACT.json](02_OFFICIAL_CONTRACT.json).
Es un extracto de documentación, no una copia de la base EC3.

| Operación | Contrato oficial consumido |
|---|---|
| Host | `https://openepd.buildingtransparency.org/api` |
| Autenticación | `Authorization: Bearer <token>`; también admite un access token obtenido externamente mediante OAuth |
| Búsqueda | `GET /v2/epds/search`, parámetros `omf`, `page_number`, `page_size` |
| Paginación | páginas desde 1, `payload` + `meta.paging.total_count/total_pages/page_size` |
| Detalle | `GET /epds/{openXpdUuid}`, objeto `EPD--Full` |
| Valor utilizado | `impacts[LCIA explícita].gwp.A1A2A3.mean`, unidad explícita `kgCO2e` |
| Unidad de referencia | `declared_unit.qty` / `declared_unit.unit` |
| Versiones | `version` entero upstream; `program_operator_version` separado; secuencia local por payload nuevo |

Fuentes oficiales:

- [OpenAPI](https://docs.open-epd-forum.org/openapi/openepd-rest.json).
- [Guía y clave de API](https://docs.open-epd-forum.org/en/guides/python-openepd-quickstart/).
- [Costes por operación y atribución](https://docs.buildingtransparency.org/ec3/api-and-integrations).
- [Acceso y derechos de uso](https://www.buildingtransparency.org/api-access-pricing/).

La guía publica coste 1.0 para Get OpenEPD y Get Material List. Cada intento de
consulta implementada reserva un token. El presupuesto local es el autorizado
por el usuario: **100 tokens en cualquier ventana de 60 segundos**, compartido
por workers y jobs de esta instalación. No se sustituyó por los límites genéricos
de otras cuentas. El operador debe coordinar cualquier otro consumidor de la
misma cuenta que esté fuera de esta base PostgreSQL; no puede compartir claves
con otro cliente y esperar que este limiter vea su consumo.

No se reutilizan costes de endpoints EC3 privados ni se interpretan tokens como
tokens LLM. Si Building Transparency cambia el contrato/coste, verificar la
documentación y actualizar cliente/pruebas antes de habilitar nuevos endpoints.

## Configuración backend

| Variable | Valor inicial / significado |
|---|---|
| `EC3_ENABLED` | `false`; bloquea red, ingestión y nueva elegibilidad EC3 |
| `EC3_API_TOKEN` | secreto Bearer de EC3/openEPD, scope de lectura; nunca en frontend/logs/repositorio |
| `EC3_STORAGE_ALLOWED` | `false`; habilitar sólo con derechos de cache y evidencia de auditoría documentados |
| `EC3_RIGHTS_REFERENCE` | referencia interna no secreta al acuerdo de Building Transparency |
| `EC3_RIGHTS_VALID_UNTIL` | fecha ISO `YYYY-MM-DD` de vigencia del permiso |
| `EC3_CACHE_TTL_SECONDS` | `300`, máximo 3600, `0` deshabilita cache |
| `EC3_EVIDENCE_MAX_AGE_HOURS` | `168`, limitado además por la política de fuente |

El rate limiter requiere PostgreSQL; falla cerrado en SQLite. La app no obtiene
tokens mediante contraseñas ni almacena refresh tokens: la rotación del Bearer
se realiza en el gestor de secretos/entorno del despliegue. Se rechazan redirects;
el destino HTTPS es fijo y no existe base URL controlable por un usuario.

La cuenta Pilot habilitada no se toma como autorización implícita de todos los
derechos de almacenamiento comercial. Si el acuerdo no autoriza persistencia,
search/detail funcionan sin cache y la ingestión permanece bloqueada. Para
habilitar evidencia inmutable, el acuerdo debe contemplar su conservación para
auditar cálculos históricos. No activar esta opción si exige borrar esa evidencia
al terminar el piloto sin haber acordado el tratamiento de esos históricos.

Al vencer derechos se bloquean cache y nueva elegibilidad. El job
`purge_ec3_cache --all` elimina físicamente el cache; no borra decisiones ni
cálculos históricos. La copia mínima de evidencia existente permanece protegida
para auditoría, conforme al permiso que debe documentarse antes de ingerir.

## Persistencia y trazabilidad

Una ingestión usa un ID explícito y fuerza una lectura fresca de detalle. Publica
un `SyncRun` no autoritativo, un `ExternalSnapshot` sin payload/texto completos,
un `ExternalRecord` y un `EpdVersion` inmutable. Almacena la proyección de campos
necesarios: identidad, unidad, fechas, programa/PCR/estándar/verificador,
geografía declarada, especificidad disponible y GWP A1-A3 por método declarado.
No almacena discusiones LCA extensas, imágenes, contactos personales ni PDFs.

El checksum upstream es SHA-256 del cuerpo HTTP decodificado (antes de parsear
JSON); un segundo SHA-256 cubre la proyección canónica persistida. No se afirma
que la proyección permita reconstruir bytes omitidos. Una recuperación idéntica
conserva snapshot/versión originales y actualiza `last_seen_at`; un payload nuevo
crea una versión local aunque el proveedor no aumente su número. Un retorno
A → B → A crea otra versión local de evidencia, con nueva fecha de recuperación,
sin reutilizar aprobaciones antiguas aunque comparta el snapshot de bytes de A.
Las consultas
fallidas no implican retiro ni desaparición.

`provenance()` y el contexto del factor/version responden fuente, ID externo,
EPD, versión upstream/local, recuperación original, unidad, lifecycle scope,
checksum y metadatos de calidad. Los datos ausentes permanecen nulos y bloquean
la promoción cuando son necesarios; no se inventa calidad, vigencia ni autoridad.
La observación de frescura actual está en `ExternalRecord.last_seen_at`.
El ledger existente añade `external_source`, `ec3_candidate_id` y `ec3_review_id`
desde el snapshot técnico congelado del cálculo. Su quality adapter describe
metadatos históricos; la vigencia actual se evalúa separadamente en el selector.
No se rellenan los identificadores específicos de ÖKOBAUDAT con identificadores EC3.

## API DRF interna

Prefijo `/api/integrations/ec3/`. Requiere sesión autenticada de **superusuario
activo**, consistente con la gobernanza global de fuentes existentes. Un
administrador de tenant o una cuenta IA no obtiene automáticamente acceso a esta
API. Los mappings resultantes son del tenant del material y reutilizan sus
servicios/permisos existentes. No hay endpoint de confirmación de evidencia por IA.

| Método/ruta | Entrada y resultado |
|---|---|
| GET `search/` | `omf`, `page_number=1`, `page_size=5` (máx. local 25); una página, atribución, checksum, recuperación |
| GET `epds/<id>/` | detalle proyectado, sin persistir evidencia ni confirmar aplicación |
| POST `epds/<id>/ingest/` | `{}`; publica knowledge dirigido y devuelve `epd_version_id` |
| GET `candidates/?material_id=<id>&page=1` | candidatos del material, paginación 25, ausencia `UNMAPPED` |
| POST `candidates/` | `material_id`, `epd_version_id`; candidato idempotente |
| GET `candidates/<id>/` | estado derivado, provenance, historial y contrato futuro |
| POST `candidates/<id>/review/` | `decision=approved/rejected`, `lcia_method`, `context` de revisión humana |
| POST `candidates/<id>/promote/` | `{}`; exclusivamente factor/versión **borrador**, sin activación |
| POST `candidates/<id>/mapping/` | `vigencia_desde`, `vigencia_hasta` opcional; mapping **propuesto** |
| GET `candidates/<id>/eligibility/` | `lcia_method`; verificación explícita de elegibilidad científica (mismo `evaluate_version` interno, sin efectos secundarios) |
| GET `epds/<epd_id>/versions/` | historial local completo de versiones de una EPD ya conocida, con provenance por versión |
| GET `candidates/<id>/compare/?candidate_b=<id>&lcia_method=` | comparabilidad determinista entre dos candidatos EC3 ya propuestos (`COMPARABLE`/`PARTIALLY_COMPARABLE`/`NOT_COMPARABLE`/`REVIEW_REQUIRED`) y, si aplica, la diferencia normalizada |
| GET `materials/<material_id>/opportunities/?lcia_method=` | previsualización de candidatos EC3 ya propuestos para ese material, aún no aplicados, frente al factor activo actual |
| GET `observability/` | resumen operativo derivado (solicitudes, errores por causa saneada, tokens consumidos, cache, EPDs/versiones/candidatos/revisiones conocidos) |

La revisión requiere seis textos no vacíos: `technical_basis`, `geographic_basis`,
`temporal_basis`, `standard_basis`, `verification_basis`, `note`. Es el profesional
quien debe verificar su correspondencia documental, uso, región, tiempo y método.
La comprobación mecánica no acredita por sí misma esa correspondencia. No se
elige entre LCIA methods ni se suman scopes automáticamente. No se usa el valor
de EC3 ajustado por incertidumbre como reemplazo del GWP declarado. GWP negativo
queda bloqueado en esta fase: su uso requiere un contrato ampliado que conserve
y evalúe evidencia de remociones/carbono biogénico, fuera del E2E de acero.

Tras promoción, la activación sigue `factor_governance`: borrador → pruebas →
validado → activo. La aprobación/revocación del mapping sigue la API existente de
`material_factor_mapping`. El selector revalida la evidencia EC3 en cada nueva
selección; una EPD nueva, obsoleta, expirada o sin derechos vigentes bloquea el uso.
No se alteran cálculos históricos ni se recalculan automáticamente.

Estados de candidato: `CANDIDATES_FOUND` al proponer; `REVIEW_REQUIRED` tras
revisión/promoción hasta completar la gobernanza; `MAPPED` con mapping aprobado,
versión activa y compatibilidad actual; `REJECTED` tras rechazo/revocación;
`STALE` si la fuente/evidencia pierde vigencia. `MAPPED` describe el vínculo,
no sustituye la elegibilidad por fecha/unidad/contexto de cada actividad.

Errores: 400 validación/configuración, 401/403 autenticación/autorización local,
404 EPD/recurso ausente, 429 presupuesto o throttling upstream con `Retry-After`,
502 proveedor/transporte/schema. Nunca se devuelve el cuerpo de error upstream.
Máximo tres intentos, backoff exponencial con jitter, timeout conexión/lectura
5/20 s y respuesta máxima 2 MiB. Esperas upstream mayores de 8 s se devuelven como
429 con diferimiento compartido, para no ocupar el worker durante esperas largas.

## Jobs y SOURCE-WATCH

```sh
python backend/manage.py check
python backend/manage.py migrate --plan
python backend/manage.py migrate
python backend/manage.py ingest_ec3_epd <OPENXPD_ID_REAL> --actor-id <REVISOR_ID>
python backend/manage.py refresh_known_ec3_epds --actor-id <REVISOR_ID> [--limit N]
python backend/manage.py purge_ec3_cache
```

Programar `purge_ec3_cache` periódicamente (por ejemplo cada 5 minutos). Al retirar
derechos/rotar cuenta ejecutar `purge_ec3_cache --all`. Cada ingestión dirigida,
incluida una ejecución manual programada por el operador, exige un ID concreto; no
existe un job que descubra o importe EPDs nuevas por sí mismo.

`refresh_known_ec3_epds` re-valida (nunca descubre) cada EPD que Carbono Zero ya
conoce localmente para esta fuente, una por una, mediante la misma ingesta dirigida
y auditada de siempre (`ingest_ec3_epd`/`services.ingest_epd`) — nunca vuelca el
catálogo EC3. Es idempotente: una EPD sin cambios reales sólo confirma frescura, sin
crear una versión local duplicada; un cambio real crea una nueva versión local,
igual que una ingestión manual. Respeta el presupuesto compartido de 100
tokens/minuto: ante un `RateLimited` espera el `retry_after` indicado y reintenta la
misma EPD una vez antes de continuar con la siguiente (continue-on-error: una EPD
que falla — 404, 5xx, timeout, rate limit persistente — nunca aborta el lote
completo). Ningún comando promueve factores ni aprueba mappings.

El registro de conector se añade desde `Ec3Config.ready()` a la interfaz de
registro existente, sin editar SOURCE-WATCH. No declara polling seguro; `fetch`
rechaza sincronización genérica. Los jobs oficiales de SOURCE-WATCH permanecen
sin cambios. Los facts EC3 no se fuerzan en candidatos específicos de ÖKOBAUDAT
o HuellaChile. Migraciones EC3 dependen de knowledge 0013 y analytics 0076;
no se insertan en la secuencia de migraciones SOURCE-WATCH.

## Comparabilidad y oportunidad potencial

Cada candidato sigue exponiendo `recommendation_contract` versión `EC3-01/v1` sin
cambios (`hotspot`/`potential_reduction` nulos, `ai_may_confirm=false`) — ese campo
describe un contrato de tarjeta de UI, no el motor real.

El motor real vive en dos capas distintas, deliberadamente NO fusionadas:

1. **Reutilización directa (sin código nuevo).** En cuanto un candidato EC3 llega a
   `MAPPED` (mapping aprobado, versión `activo`, elegibilidad vigente), el material
   al que está mapeado participa automáticamente en el motor de hotspots/conjuntos
   comparables/oportunidades **ya existente y sin modificar** de MATERIAL-INTELLIGENCE
   (`apps.analytics.services.material_hotspots.material_hotspots`,
   `material_comparable_sets.comparable_alternatives`,
   `material_opportunities.detect_opportunities`) — porque ese motor sólo exige un
   `VersionFactorAmbiental` activo vía `select_material_factor` (que ya invoca el guard
   `factor_block_reason` de EC3) y una `standard` EN 15804 explícita. Esta sesión
   auditó esa ruta y encontró que `ec3.reporting.factor_quality` nunca poblaba esa
   `standard` — cualquier material mapeado a EC3 quedaba permanentemente excluido
   (`standard_unknown`) sin importar cuán correctamente estuviera aprobado. Se corrigió
   derivando `standard` de la lista `compliance` real de la EPD (p. ej. `"EN
   15804+A2"`), nunca inventada: si la EPD no declara una generación EN 15804
   explícita, `standard` permanece `None` y el material sigue correctamente excluido.
   Prueba de regresión:
   `apps.ec3.tests.test_comparability_opportunity.CrossSourceReuseTests` — un material
   mapeado a EC3 y uno mapeado a ÖKOBAUDAT resultan mutuamente comparables por el
   mismo motor, sin ninguna rama EC3-específica en `material_comparable_sets.py`.

2. **Previsualización EC3 pre-decisional (`apps/ec3/comparability.py` y
   `apps/ec3/opportunity.py`, nuevos).** Cubre el caso que el motor anterior no
   cubre: candidatos EC3 ya propuestos (`propose_candidate`) por un humano pero
   **todavía no mapeados/activos**. `comparability.compare_epd_versions` compara dos
   EPDs ya ingeridas de forma determinista y explicable (categoría EC3, tipo de
   unidad declarada, geografía declarada, lifecycle scope, método LCIA, PCR) →
   `COMPARABLE`/`PARTIALLY_COMPARABLE`/`NOT_COMPARABLE`/`REVIEW_REQUIRED`, nunca una
   similitud. `opportunity.material_candidate_opportunities` previsualiza, para un
   material, cada candidato EC3 aún no aplicado frente al factor activo actual
   (reutilizando `select_material_factor` y la conversión de unidades existente
   `unit_conversion.convert_value` — nunca una conversión inventada). Todo resultado
   lleva `requires_human_review=true`, nunca decide viabilidad de compra ni cumplimiento
   normativo, y nunca busca ni propone candidatos por sí mismo — sólo informa sobre
   lo que un humano ya propuso. Expuesto vía
   `candidates/<id>/compare/` y `materials/<id>/opportunities/`.

## Troubleshooting

Cada fallo de ingestión queda en `SyncRun.message` (nunca un cuerpo/credencial),
consultable también agregado por causa en `GET /api/integrations/ec3/observability/`:

| `message` | Causa | Acción |
|---|---|---|
| `ec3_rate_limited` | Presupuesto de 100 tokens/min agotado (local o 429 upstream) | Esperar el `Retry-After`/`retry_after` devuelto; no reintentar en bucle ajustado |
| `ec3_authentication_failed` (401) | `EC3_API_TOKEN` inválido/rotado | Verificar el secreto en el gestor de entorno, nunca en el repositorio |
| `ec3_access_denied` (403) | Cuenta/scope Pilot sin acceso a ese recurso | Confirmar alcance Pilot con Building Transparency |
| `ec3_epd_not_found` (404) | ID inexistente o retirado | Confirmar el ID; no reintentar indefinidamente |
| `ec3_unavailable` / `ec3_network_timeout` / `ec3_transport_error` | 5xx, timeout o corte de transporte tras reintentos | Reintentar más tarde; no indica retiro ni desaparición del EPD |
| `ec3_schema_invalid` / `ec3_response_too_large` / `ec3_invalid_content_type` | Respuesta no conforme al contrato oficial documentado | Verificar si Building Transparency cambió el contrato antes de asumir un bug local |
| `ec3_ingestion_failed` | Error no upstream (p. ej. de aplicación) | Revisar logs de aplicación de ese proceso; nunca contiene el secreto |

Una ingestión fallida nunca marca el `ExternalRecord` como retirado ni reescribe
cálculos históricos; sólo bloquea usos *nuevos* mediante `evaluate_version`.

## Rollback

No existe una migración de datos "irreversible" propia de esta fase: EC3 no borra
ni reescribe historia (evidencia, revisiones y versiones son inmutables por diseño).
Para desactivar la integración sin perder trazabilidad:

1. `EC3_ENABLED=false` — bloquea inmediatamente red, ingestión y nueva elegibilidad;
   los mappings ya aprobados con evidencia EC3 dejan de ser seleccionables
   (`evaluate_version` añade `ec3_disabled`), pero los cálculos históricos y su
   provenance permanecen intactos y consultables.
2. Para retirar un mapping específico, usar el mecanismo existente
   `material_factor_mapping.revoke_material_mapping` (nunca borrar filas
   directamente) — preserva el historial de por qué se retiró.
3. `purge_ec3_cache --all` elimina sólo el cache de respuestas (nunca evidencia
   auditada ni decisiones).
4. Revertir las migraciones `0001`–`0003` de `apps.ec3` sólo si se decide remover la
   app por completo; esto es destructivo para `EpdVersion`/`Candidate`/`Review` y
   requiere primero confirmar que ningún `VersionFactorAmbiental`/mapping activo
   depende de esa evidencia (ver `factor_block_reason`). No se ejecutó ni se probó
   esta reversión en esta fase — es un procedimiento documentado, no verificado.
5. No hay rollback de código especial: revertir el commit correspondiente (esta
   fase no crea commit) restaura el estado de archivos sin tocar la base de datos.
