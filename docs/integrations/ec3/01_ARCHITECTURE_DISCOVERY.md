# EC3-01 — Architecture discovery

Fecha: 2026-09-12. Descubrimiento realizado antes de modificar código.

## Inspección y límites

Se inventarió el repositorio completo (backend Django/DRF, frontend React/Vite,
scripts, src analítico, tests, infraestructura y documentación). No se encontraron
AGENTS.md aplicables. Se contrastaron los documentos ai-context, MATERIAL-DATA,
SOURCE-WATCH y los modelos, servicios, selectores, conectores y pruebas reales.

El working tree contiene trabajo concurrente SOURCE-WATCH en knowledge/models.py,
services.py, urls.py, views.py, nuevas migraciones 0014–0018 y módulos/tests de
watch policy, health, observation, classification, routing y review queue.
Estos archivos quedan fuera del alcance de edición. No se hará commit/push.

## Arquitectura existente y reutilización

| Capa | Implementación real | Decisión EC3 |
|---|---|---|
| Fuente externa | knowledge.EnvironmentalSource, SourceState | Reutilizar identidad, autoridad y política de fuente; sin polling de catálogo |
| Ingestión externa | connectors/base.py, registry.py, SyncRun | Ingestión dirigida a un ID, job explícito; jamás snapshot completo autoritativo |
| Knowledge/versiones | ExternalRecord, ExternalSnapshot, hashes, facts tipados por proveedor | Reutilizar snapshot/registro/run; fact EC3 en app aislada |
| SOURCE-WATCH | watch_policy, source_health, watch_orchestration, change_observation/classification, impact_routing, review_queue | Sin cambios; no declarar soporte de watch automático ni usar ausencias de búsquedas como retiros |
| Captura operacional | ActividadOperacional, Observacion, FuenteDatos, EvidenciaObra/VersionEvidencia; ProcesoIngesta y jobs de evidencia | EC3 no crea observaciones operacionales ni confirma evidencia |
| Materiales | MaterialOperacional, EventoMaterial; recepción como punto contable A1-A3 | Usar material y evento existentes |
| Candidatos | EnvironmentalFactorCandidate exclusivo HuellaChile; MaterialEnvironmentalFactorCandidate exclusivo ÖKOBAUDAT | No forzar facts EC3 en relaciones específicas de otros proveedores |
| Factores | FactorAmbiental, VersionFactorAmbiental; factor_governance | Promover únicamente a borrador con revisión explícita y provenance |
| Mapping | MaterialFactorMapping + decisiones, material_factor_mapping.py | Reutilizar propose/approve/reject/revoke y permisos; nunca matching automático |
| Elegibilidad | material_factor_selector, eligibility_v2, methodology_selector | Factor activo, mapping aprobado, fechas/unidades compatibles y revisión EC3 vigente |
| Motor | generic_environmental_engine, calculation_v2, CalculoAmbiental, snapshot_tecnico | Conectar por factores versionados; preservar cálculos anteriores |
| Futuro recomendador | material_hotspots, comparable_sets, suitability, opportunities, copilot | Contrato de candidatos con comparabilidad pendiente; no implementar recomendador nuevo |

## Diseño modular previsto

App `apps.ec3` con cliente, schemas, rate limiter compartido, cache condicionado
por derechos, modelos/facts y decisiones, servicios, endpoints DRF y comando de
ingestión dirigida. Migraciones propias, dependientes de las migraciones ya
estables de knowledge/analytics. Puntos de conexión mínimos: settings, URL raíz,
registro del conector mediante AppConfig y guard de elegibilidad de factores EC3.
No refactor de código SOURCE-WATCH. El conector rechazará sincronizaciones masivas.

Los snapshots conservarán hash del JSON completo procesado, identificadores,
versión upstream separada de versión local, recuperación y proyección mínima de
evidencia; no copiarán el payload completo ni PDFs. La retención y el cache estarán
deshabilitados sin configuración explícita del acuerdo habilitante. Los mocks se
identificarán como sintéticos y no como evidencia EC3 real.

## Contrato oficial y verificación pendiente

Documentación consultada:

- https://docs.open-epd-forum.org/en/rest-api/ publica su especificación en
  https://docs.open-epd-forum.org/openapi/openepd-rest.json
- https://docs.open-epd-forum.org/en/guides/python-openepd-quickstart/ confirma host
  `https://openepd.buildingtransparency.org/api`, búsqueda oMF y API token.
- https://docs.open-epd-forum.org/en/open-epd-format-1/ describe el formato.
- https://www.buildingtransparency.org/api-access-pricing/ y los términos enlazados
  distinguen acceso de derechos de almacenamiento/cache. Pilot confirmado por el
  usuario no se interpreta por sí solo como permiso de persistencia comercial.

Se verificará el OpenAPI antes de codificar rutas, parámetros, autenticación,
costes por operación, paginación o campos. El presupuesto confirmado es 100 tokens
por minuto, no 100 requests por minuto. No se usarán credenciales ni datos reales
sin configuración backend; el smoke autenticado quedará bloqueado exactamente
en la ausencia de la variable del token, mientras se completa el trabajo offline.

## Decisiones confirmadas durante implementación

El checksum primario cubre bytes completos del cuerpo HTTP decodificado, antes
del parseo; el secundario cubre la proyección JSON canónica mínima. Se añaden
adaptadores de lectura pequeños en `material_quality` y `material_ledger` para
exponer la provenance EC3 a través del ledger existente sin refactorizarlo.
Los campos específicos de ÖKOBAUDAT no se rellenan con IDs EC3.

Una reversión upstream A → B → A crea otra observación local/version con
recuperación propia, compartiendo el snapshot de bytes pero sin resucitar una
aprobación anterior. Los fallos de revalidación se registran y bloquean nuevas
selecciones hasta recuperación; no se declaran como retiro de catálogo.
