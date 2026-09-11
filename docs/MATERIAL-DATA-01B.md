# MATERIAL-DATA-01B — detalles y perfiles ambientales ÖKOBAUDAT

Implementación sobre `main`, sin commit ni push. Evidencia real: [smoke JSON](material-data-01b-smoke.json).

## Arquitectura

- `connectors/okobaudat_detail.py`: descarga acotada y parser ILCD 1.1 / EPD 2013 con namespaces verificados en XML oficial.
- `okobaudat_detail_sync.py`: hidratación incremental por UUID + versión; observaciones durables antes de materializar; transacción independiente para cada perfil y todos sus indicadores.
- `OekobaudatEnvironmentalProfileFact`: vínculo al `OekobaudatProcessFact`, identidad exacta, estándar, cantidad/unidad declaradas, snapshot y referencias históricas.
- `OekobaudatEnvironmentalIndicatorFact`: identidad y versión upstream, nombre, código, valor decimal textual exacto, unidad e identidad de unidad, módulo, estándar y provenance vía snapshot/perfil.
- `ExternalSnapshot`: conserva los bytes originales en base64 y SHA-256 de esos bytes, URL solicitada, hora de recuperación y metadata. Record kinds: `okobaudat_process_detail` y `okobaudat_detail_reference`.
- La publicación consiste en la existencia del perfil completo confirmado en base de datos. No agrega `ExternalRecord` ni cambia `SourceState` del catálogo; 01A y las otras fuentes mantienen su ciclo de publicación.
- Inmutabilidad ORM y creación gobernada de facts; PostgreSQL además impide UPDATE/DELETE de facts y snapshots de detalle mediante triggers. Restricciones únicas de identidad y CHECK para A1-A3.

Migraciones: `0012_oekobaudatenvironmentalprofilefact_and_more` crea los dos modelos; `0013_okobaudat_detail_history_guards` instala protecciones PostgreSQL reversibles. No transforma datos 01A.

## Contrato contrastado con upstream

La [guía oficial ECO Platform](https://data.eco-platform.org/static/doc/ECO_Portal_API_-_Quickstart_Guide.pdf) documenta `format=XML` y `view=extended`. En este servidor, el enlace del catálogo sin `format=XML` redirige a HTML; `view=extended` no incorpora la unidad del flujo de referencia. Se utiliza:

`https://www.oekobaudat.de/OEKOBAU.DAT/resource/processes/{uuid}?format=XML&version={version}`

1. `processInformation/quantitativeReference/referenceToReferenceFlow` identifica un único intercambio. El A2 observado omite `type`; se acepta la referencia explícita sin ese atributo.
2. Se conserva `resultingAmount`, o `meanAmount` cuando no hay resultado explícito.
3. El flujo referencia una propiedad mediante su ID interno; esa propiedad referencia un grupo de unidades. El grupo identifica la unidad de referencia por ID interno. Cantidad declarada = cantidad del intercambio × `meanValue` de la propiedad de referencia. Se conservan ambos operandos, sin convertir unidades.
4. Las referencias con versión se resuelven exactamente. Si upstream omite versión, se conserva la primera respuesta oficial observada, su versión real y snapshot; reanudar utiliza esa misma evidencia. No se siguen URIs de terceros incrustadas en XML.
5. `LCIAResults/LCIAResult` y los intercambios con resultados contienen `common:other/epd:amount`, con atributos `epd:module` y, en algunos módulos, `epd:scenario`. La unidad está en `epd:referenceToUnitGroupDataSet`.
6. Sólo se materializan valores explícitos `A1-A3`. No se suman A1, A2 y A3 ni se publican A4/A5 u otros módulos. Escenarios múltiples, duplicados o módulos ambiguos fallan antes de publicar.
7. El estándar se obtiene de las referencias oficiales de cumplimiento, contrastadas con 01A. GWP A1 y las cuatro identidades GWP A2 tienen una tabla exacta de UUIDs observados; jamás se convierten ni se fusionan.
8. Otros indicadores conservan nombre, UUID y versión; su código es el UUID, sin deducir semántica del nombre. Unidades explícitas desconocidas se preservan literalmente con su identidad, sin conversión. Una unidad ausente impide publicar. `unknown` no declara alcance operativo.

Los [fixtures oficiales y su manifiesto](../backend/apps/knowledge/fixtures/okobaudat_detail/manifest.json) permiten reproducir el parsing sin red.

## API autenticada, sólo GET

Prefijo `/api/knowledge/materials/oekobaudat/`:

- `profiles/` y `profiles/<id>/`
- `indicators/` y `indicators/<id>/`

Filtros: `uuid`/`process_uuid`, `version`/`dataset_version`, `standard`, `indicator` (código exacto), `module`. Paginación: 50 por defecto, máximo 200. El perfil incluye sus indicadores y provenance de dependencias; cada indicador referencia su perfil y snapshot. `freshness` mide la edad de recuperación del detalle usando `stale_after_hours` de la fuente, independientemente de una actualización posterior del catálogo. No expresa vigencia de una EPD ni equivalencia metodológica.

## Operación y reanudación

```sh
python manage.py hydrate_okobaudat_process_details --limit 20 --batch-size 100 --delay 1
python manage.py hydrate_okobaudat_process_details --process-uuid c54c16f6-4295-4749-bff0-ba7ed4bc9117 --dataset-version 00.01.000
```

`--limit` limita identidades pendientes; repetir avanza después de las hidratadas. `--batch-size` limita la lectura por cursor; cada perfil tiene su propia transacción. El resumen informa candidatos, ya hidratados, descargados, materializados, omitidos, fallidos e indicadores creados. `SyncRun` conserva progreso por identidad y errores sanitizados. Un proceso fallido no altera otros perfiles.

PostgreSQL usa un advisory lock de sesión por identidad durante descarga y publicación; otro worker omite esa identidad y puede reintentarlo. El servidor libera el lock al desconectarse el worker. La restricción única impide duplicados como segunda defensa. Usar conexión PostgreSQL directa o pooling de sesión, no transaction pooling. SQLite es sólo una alternativa de desarrollo con bloqueo dentro del proceso; no soporta workers distribuidos.

Los snapshots observados se reutilizan incluso después de fallo/interrupción. `--refetch-failed-reason "razón técnica/upstream documentada"` permite una nueva observación sólo para identidades aún no materializadas; conserva las observaciones anteriores. Nunca rehidrata una identidad publicada. Un cambio de parser no reemplaza hechos históricos: requerirá una política futura explícita de revisión.

Descarga con HTTPS y ruta/host/parámetros canónicos; rechaza redirects, puertos alternativos, credenciales y destinos ajenos. Límite de bytes descomprimidos, content type XML, timeouts, tres intentos para fallos transitorios y espera de `Retry-After`. Si upstream solicita más de 30 segundos o persiste la limitación/indisponibilidad HTTP, el resto del lote queda pendiente para otra ejecución. XML sin DTD/entidades. No se guardan mensajes arbitrarios de excepciones. Se conservan los términos de uso de 01A en los snapshots y respuestas API.

## Smoke real y límites

El smoke del 2026-09-11 usa exclusivamente dos procesos oficiales en PostgreSQL local aislado:

| Estándar | UUID / versión | Cantidad declarada | Indicadores A1-A3 | GWP A1-A3 |
|---|---|---|---|---|
| A2 | `c54c16f6-4295-4749-bff0-ba7ed4bc9117` / `00.01.000` | 1000 kg | 37 | GWP-total `847.351015163189` kg CO_(2) eq |
| A1 | `f63ac879-fa7d-4f91-813e-e816cbdf1927` / `00.00.025` | 1 m3 | 25 | GWP `-647.4201396839651` kg CO2-?qv. |

A2 conserva separadamente fossil `933.522267135669`, biogenic `-86.3889351705048` y luluc `0.217683198024282`. Segunda ejecución: dos ya hidratados, cero descargas. El JSON enlazado incluye snapshots, hashes, URLs, timestamps, dependencias y todos los indicadores.

No se hidrataron los ~4284 procesos ni se modificó producción. Variantes upstream sin A1-A3 explícito o con referencias incompatibles quedan sin publicar hasta resolver su contrato; los dos ejemplos no prueban cobertura de todo el catálogo. La resolución de referencias sin versión es una limitación real upstream, hecha explícita y congelada en provenance. No se implementan matching, factores operativos, cálculos de materiales, recomendaciones ni frontend.

## Validación

Entorno final: Python 3.13, Django 6.0.4, DRF 3.17.1 y PostgreSQL 18.3 local aislado. Django/DRF coinciden con `backend/requirements.txt`.

- 30 pruebas nuevas y la prueba de concurrencia legal: **31/31 OK**, 30.140 s. Incluyen restricciones PostgreSQL reales, dos workers, integridad histórica, seguridad HTTP/XML, fallo tras insertar el primer indicador, reanudación, límites incrementales, pausa upstream y API.
- `manage.py check`: sin incidencias; `makemigrations --check --dry-run`: sin cambios pendientes.
- Reconstrucción de ambos perfiles reales desde sus snapshots y dependencias, sin red: cantidades y todos los campos de indicadores coinciden exactamente.
- Smoke: 2/2 perfiles, 62 indicadores; repetición del comando con Django 6.0.4: cero descargas.

La primera ejecución amplia con Django 5.2.5 detectó una dependencia de orden en la limpieza de pruebas PostgreSQL. La prueba nueva ahora conserva `django_migrations` y emite `post_migrate` tras limpiar, restaurando los registros base. No se modificó lógica legal ni de otras fuentes.
