# ARQ-02A/B — Modularización física de modelos

## Baseline y objetivo

- Baseline auditado: `6937c26aa397a99106653836372a1b2f710d4e18`.
- Alcance implementado: scaffold del package `apps.analytics.models` y extracción exclusiva de los modelos Platform.
- Invariante principal: reorganización física sin cambios de esquema, API o comportamiento.

## Estrategia aplicada

`backend/apps/analytics/models.py` se convirtió atómicamente en el package
`backend/apps/analytics/models/`. El contenido todavía no modularizado permanece en
`models/__init__.py`, que continúa siendo la API pública consumida por el repositorio.

Los modelos extraídos se importan y reexportan explícitamente desde `models/__init__.py`.
No existen definiciones duplicadas ni se modificaron los imports consumidores.

Los helpers puros `normalize_key` y `unique_code` viven en `models/utils.py`. Se
reexportan desde la API pública para conservar imports existentes y son utilizados por
`platform.py` sin importar el módulo `__init__`, evitando un ciclo.

## Modelos movidos

Los únicos modelos trasladados a `models/platform.py` son:

- `Organizacion`
- `SuscripcionSaaS`
- `EventoAuditoriaSaaS`
- `UsuarioOrganizacion`
- `UsuarioObraAcceso`

`UsuarioObraAcceso.obra` conserva una relación diferida con `analytics.Obra`, ya que
`Obra` permanece deliberadamente en la API pública durante esta fase.

## Imports y ciclos

- La API `apps.analytics.models` sigue exportando modelos movidos y no movidos.
- Los imports locales de servicios existentes en el antiguo archivo se ajustaron un
  nivel (`..services`) por la nueva ubicación física del package.
- Las cuatro señales `pre_delete` existentes permanecen en `models/__init__.py` y se
  registran una sola vez durante la carga normal del app.
- `admin.py`, IoT, serializers, vistas, servicios y comandos siguen consumiendo la API
  pública sin cambios.
- Las migraciones históricas que importan `apps.analytics.models` continúan encontrando
  los callbacks de archivos reexportados. No se editaron migraciones históricas.

## Invariantes verificadas

Los cinco modelos conservan:

- `app_label = "analytics"`;
- los mismos nombres de clase;
- las tablas `analytics_organizacion`, `analytics_suscripcionsaas`,
  `analytics_eventoauditoriasaas`, `analytics_usuarioorganizacion` y
  `analytics_usuarioobraacceso`;
- relaciones, constraints, choices, `Meta` y métodos existentes.

El registry contiene 94 modelos `analytics` y 94 etiquetas únicas, sin registros
duplicados.

## Validación ejecutada

- `python manage.py check`: correcto, sin incidencias.
- `python manage.py makemigrations --check --dry-run`: `No changes detected`.
  La conexión PostgreSQL configurada no estaba disponible y emitió un warning de
  timeout al comprobar el historial, sin impedir la detección local del estado.
- `python manage.py test apps.analytics.test_model_modularization` usando SQLite de
  pruebas: 7/7 correctos, incluida persistencia de organización y membresía.
- Suite transversal solicitada (permisos, onboarding, contexto operacional, cálculo,
  factores y registro manual): 127 ejecutados; 122 correctos y 5 fallos preexistentes
  ajenos a esta extracción. Los fallos restantes corresponden a catálogo legacy de
  áreas de onboarding (3), `DocumentoAmbientalSerializer` enviando
  `perfil_ambiental` al modelo (1) y una discrepancia histórica SQLite para
  `AccionAmbiental.organizacion_id` (1).

Durante la primera ejecución transversal se detectaron dos imports relativos de
servicios afectados por el cambio archivo→package. Se corrigieron y la repetición no
volvió a presentar errores atribuibles a ARQ-02.

## Deuda deliberadamente no tocada

- No se modularizaron otros modelos.
- No se movieron señales a módulos dedicados.
- No se cambiaron servicios, serializers, endpoints, permisos, IoT ni frontend.
- No se corrigieron los cinco fallos transversales no relacionados descritos arriba.
- No se crearon migraciones.

## Siguiente bloque recomendado

ARQ-02C puede abordar Operational Context / Work / Area en una entrega separada,
después de cerrar o aceptar explícitamente la deuda de tests preexistente. Esta entrega
se detiene en ARQ-02A/B.

## ARQ-02C — Operational Context

### Modelos y owner físico

ARQ-02C extrae conjuntamente a `models/operational_context.py`:

- `EtapaObra`
- `Obra`
- `AreaOperacional`
- `EspacioTrabajoOperacional`
- `UnidadOperacional`
- `ProcesoOperacional`

El agrupamiento conserva la estabilidad entre Operations y Platform Context sin crear
dos módulos mutuamente dependientes. La API pública continúa reexportando los seis
modelos desde `apps.analytics.models`.

### Dependencias

El módulo depende directamente de:

- `Organizacion` y `UsuarioOrganizacion` desde `models.platform`;
- `unique_code` desde `models.utils`;
- `Decimal` y `Sum` para conservar `Obra.emisiones_kg_co2e` sin cambios.

No importa desde `models.__init__`, no requiere imports locales dinámicos y no produjo
ciclos. Los consumers externos conservan sus imports desde la API pública.

### Invariantes verificadas

Los seis modelos mantienen `app_label = "analytics"`, identidad única en el registry,
campos, relaciones, validaciones, constraints y las siguientes tablas:

- `analytics_etapaobra`
- `analytics_obra`
- `analytics_areaoperacional`
- `analytics_espaciotrabajooperacional`
- `analytics_unidadoperacional`
- `analytics_procesooperacional`

El registry permanece en 94 etiquetas únicas para 94 modelos `analytics`.

### Tests y gate funcional

- Tests arquitectónicos ampliados: 14/14 correctos.
- Se verificó persistencia de organización, obra, etapa, área, unidad, proceso,
  membresía y workspace.
- La validación cross-tenant existente del workspace continúa rechazando relaciones
  inválidas.
- `python manage.py check`: correcto.
- `python manage.py makemigrations --check --dry-run`: `No changes detected`.

La suite funcional específica de ARQ-02C ejecutó 108 tests y expuso los cinco fallos
ya aprobados como deuda, más
`ConstructionV1IntegrationTests.test_ingestion_resolves_work_into_activity`.
Este sexto test falla con `ActividadOperacional.DoesNotExist` tanto después de ARQ-02C
como en un worktree limpio de `40b41ad`, por lo que es preexistente y no fue corregido
en esta fase.

El gate del documento indica expresamente que la aparición de un sexto fallo impide
declarar ARQ-02C cerrada, aunque se haya demostrado que no es una regresión. Por ello,
la extracción queda implementada y sin regresión atribuible, pero el cierre formal queda
pendiente de aceptar o corregir esta discrepancia adicional del baseline.

### Deuda preservada y siguiente bloque

- Se mantienen sin cambios los seis fallos funcionales preexistentes observados.
- No se alteraron catálogos de onboarding, serializers, migraciones históricas,
  services, views, IoT ni frontend.
- El baseline de ARQ-02D aceptó formalmente esta discrepancia como sexto fallo
  preexistente y declaró ARQ-02C cerrado.

## ARQ-02D — Assets

### Modelos y ownership

ARQ-02D extrae exclusivamente a `models/assets.py` los modelos pertenecientes a
Operations / Assets:

- `ActivoOperacional`
- `Vehiculo`
- `Maquinaria`
- `MantenimientoActivo`
- `CondicionOperacionalActivo`
- `PuntoAmbientalOperacional`

`PuntoAmbientalOperacional` permanece en Operations porque representa ubicación y
contexto físico, no un resultado ambiental.

### Dependencias

El módulo importa directamente desde sus owners:

- `Organizacion` desde `models.platform`;
- `Obra`, `UnidadOperacional` y `ProcesoOperacional` desde
  `models.operational_context`.

La referencia de `CondicionOperacionalActivo` a `FuenteDatos`, que todavía vive en la
API pública, se mantiene como relación Django diferida `analytics.FuenteDatos`. No hay
imports desde `models.__init__` ni ciclos entre submódulos.

### Identidad de schema y registry

Los seis modelos conservan `app_label = "analytics"`, `model_name`, relaciones,
validaciones y sus tablas originales:

- `analytics_activooperacional`
- `analytics_vehiculo`
- `analytics_maquinaria`
- `analytics_mantenimientoactivo`
- `analytics_condicionoperacionalactivo`
- `analytics_puntoambientaloperacional`

La API pública, `models.assets` y Django registry apuntan a los mismos objetos de clase
6/6. El registry permanece en 94 modelos y 94 etiquetas únicas.

### Validación

- Tests arquitectónicos acumulados: 22/22 correctos.
- IoT, sensores V2, transporte y contexto operacional/RBAC: 51/51 correctos.
- Suite crítica ampliada: 136 tests; 130 correctos y los mismos seis fallos baseline.
- `python manage.py check`: correcto.
- `python manage.py makemigrations --check --dry-run`: `No changes detected`.

Los tests de Assets cubren creación de activo, vehículo, maquinaria, mantenimiento,
condición operacional y punto operacional, además de las validaciones cross-tenant
existentes. IoT y Transporte continúan consumiendo los modelos mediante
`apps.analytics.models` sin cambios.

### Deuda preservada

Se mantienen separados y sin modificar los seis fallos preexistentes aprobados:

- tres fallos del catálogo legacy de áreas/onboarding;
- `DocumentoAmbientalSerializer` y `perfil_ambiental`;
- la columna histórica SQLite `AccionAmbiental.organizacion_id`;
- `ConstructionV1IntegrationTests.test_ingestion_resolves_work_into_activity`.

No se modificaron servicios, views, serializers, permisos, IoT, transporte ni frontend.
La siguiente fase debe ser ARQ-02E y ejecutarse como entrega independiente.

## ARQ-02E — Operational Data Kernel

### Modelos y significado aprobado

ARQ-02E extrae exclusivamente a `models/operational_data.py`:

- `FuenteDatos`: origen lógico del dato;
- `ActividadOperacional`: envelope del hecho operacional;
- `Observacion`: dato atómico conocido sobre el hecho.

Esta fase solo establece ownership físico. No modifica campos, validaciones ni
comportamiento para imponer o ampliar esa interpretación semántica.

### Grafo de dependencias y relaciones

`operational_data.py` importa directamente desde sus owners:

- `Organizacion` desde `models.platform`;
- `Obra`, `UnidadOperacional` y `ProcesoOperacional` desde
  `models.operational_context`;
- `ActivoOperacional` desde `models.assets`.

Las relaciones de `Observacion` hacia `EvidenciaObra`, `VersionEvidencia` y
`RegistroExtraido` permanecen como relaciones Django diferidas al app `analytics`, ya
que esos modelos continúan deliberadamente en el package root. No se importa desde
`models.__init__` ni se generaron ciclos.

Se conservaron las relaciones de actividad con organización, obra, unidad, proceso y
activos; y las relaciones de observación con organización, actividad, fuente, actor,
evidencia, versión y registro extraído.

### Schema, API y registry

Los tres modelos conservan campos, constraints, indexes, `app_label = "analytics"` y
las tablas:

- `analytics_fuentedatos`
- `analytics_actividadoperacional`
- `analytics_observacion`

La API pública, `models.operational_data` y Django registry comparten identidad 3/3.
El registry permanece en 94 modelos y 94 etiquetas únicas.

### Consumers y tests

Los consumers de ingestion, IoT, cálculo, materiales, transporte y calidad continúan
usando `apps.analytics.models` sin modificaciones.

- Tests arquitectónicos acumulados: 29/29 correctos.
- Ingestion, Activity Core, captura manual y sector flows: 72/72 correctos.
- IoT y sensores V2: 21/21 correctos.
- Cálculo, clasificación, factores, unidades y metodología: 74/74 correctos.
- Materiales, transporte y calidad: 71/71 correctos.
- Suite crítica de baseline: 136 tests; 130 correctos y los mismos seis fallos
  preexistentes.

El sexto fallo se ejecutó antes y después. Continúa fallando en la misma línea porque
la actividad esperada no existe (`ActividadOperacional.DoesNotExist`). La ruta de la
clase en el traceback refleja el nuevo `__module__`, como exige la modularización, pero
la causa y el comportamiento funcional no cambiaron.

### Deuda preservada

- No se movieron evidencia, versiones, ingestion, transporte, materiales ni flujos.
- No se corrigieron los seis fallos baseline.
- No se modificaron services, views, serializers, permisos, IoT ni frontend.
- ARQ-02F debe ejecutarse como una fase independiente.

## ARQ-02F — Transport & Materials

### Ownership físico

ARQ-02F extrae exclusivamente los modelos modernos de transporte a
`models/transport.py`:

- `RutaOperacional`
- `ViajeOperacional`

y los modelos modernos de materiales a `models/materials.py`:

- `MaterialOperacional`
- `LoteMaterial`
- `EventoMaterial`

Los módulos importan directamente desde sus owners. Transporte depende de
`Organizacion`, `Vehiculo`, `ActividadOperacional` y `Observacion`. Materiales depende
de `Organizacion`, `ProcesoOperacional`, `FuenteDatos`, `ActividadOperacional` y
`Observacion`. Las relaciones con `Obra`, `EvidenciaObra` y `VersionEvidencia`
continúan como relaciones Django diferidas y no introducen ciclos con el package root.

### Contrato conservado

Los cinco modelos mantienen campos, choices, validaciones, constraints, indexes,
relaciones, `app_label = "analytics"` y sus tablas originales:

- `analytics_rutaoperacional`
- `analytics_viajeoperacional`
- `analytics_materialoperacional`
- `analytics_lotematerial`
- `analytics_eventomaterial`

`apps.analytics.models`, los nuevos owner modules y Django registry exponen los mismos
objetos de clase. El registry conserva 94 modelos y 94 etiquetas únicas. La extracción
no genera migraciones.

### Auditoría de modelos legacy preservados

Permanecen deliberadamente en `models.__init__` y no fueron modificados:

- `TransporteObra`: sigue activo en serializers/views legacy, administración, seeds y
  tests; mantiene escrituras propias y su integración con `RegistroEmision`.
- `TransporteLoteForestal`: sigue activo en el flujo forestal, serializers y seeds, con
  persistencia y cálculo legacy propios.
- `MaterialConstruccion`: sigue activo en administración, catálogo/views, seeds y el
  contexto ambiental legacy.
- `DatoACV`: sigue activo en el motor y contexto ambiental legacy, con lecturas y
  escrituras cubiertas por sus tests.

Estos modelos no son aliases ni reemplazos transparentes de los modelos modernos. Los
tests V2 verifican expresamente que crear registros legacy no escriba en
`ViajeOperacional` y que el catálogo `MaterialConstruccion` permanezca separado de
`MaterialOperacional`. No se implementó sincronización ni equivalencia entre ambos
mundos en esta fase.

### Gate de ARQ-02F

- Tests arquitectónicos acumulados: 34/34 correctos.
- Se cubre creación de ruta, viaje, material, lote y evento, junto con identidad de
  registry/API, relaciones y validaciones cross-tenant ya existentes.
- `python manage.py check`: correcto.
- `python manage.py makemigrations --check --dry-run`: `No changes detected`.

Las suites funcionales de transporte, materiales, ingestion, construcción y dominios
cruzados continúan consumiendo la API pública sin cambios. Los seis fallos baseline
aprobados siguen siendo deuda previa y no forman parte de esta modularización.

## ARQ-02G — Provenance & Ingestion

### Modelos y ownership

ARQ-02G separa provenance documental en `models/provenance.py`:

- `EvidenciaObra`
- `VersionEvidencia`

y el lifecycle técnico de entrada en `models/ingestion.py`:

- `PlantillaMapeo`
- `MapeoColumna`
- `ProcesoIngesta`
- `RegistroExtraido`

No se encontró otro modelo cuya responsabilidad fuese exclusivamente provenance y
que debiera incorporarse a esta fase. `FuenteDatos` permanece deliberadamente en
Operational Data. Los modelos de compliance documental también permanecen fuera.

### Dependencias y ciclos evitados

`provenance.py` importa `Organizacion` desde Platform y `AreaOperacional`, `Obra` y
`EtapaObra` desde Operational Context. `User` proviene directamente de Django. Las
relaciones históricas hacia `RegistroEmision` y `LoteForestal` son diferidas; el lookup
legacy del `save()` de evidencia obtiene el modelo resuelto desde la metadata de la
relación. Así se conserva el comportamiento sin importar `models.__init__`.

`ingestion.py` importa `Organizacion`, `FuenteDatos`, `ActividadOperacional` y
`VersionEvidencia` desde sus owners. Las relaciones inversas de `Observacion` hacia
evidencia, versión y registro extraído continúan diferidas, evitando que Operational
Data dependa de Ingestion. Los callbacks de upload se reexportan con su ruta histórica
de serialización para no alterar migrations.

### Schema, API y registry

Los seis modelos conservan campos, choices, defaults, relaciones, `on_delete`,
`related_name`, constraints, indexes, `save()`, `clean()`, `app_label = "analytics"` y
las tablas:

- `analytics_evidenciaobra`
- `analytics_versionevidencia`
- `analytics_plantillamapeo`
- `analytics_mapeocolumna`
- `analytics_procesoingesta`
- `analytics_registroextraido`

La API pública, los owner modules y Django registry comparten identidad. El registry
permanece en 94 modelos y 94 labels únicos. El raw input de un `RegistroExtraido` ya
procesado continúa siendo inmutable.

### Inventario de provenance operacional actual

- `area_origen` y `usuario_origen` viven en `EvidenciaObra`; los writers con contexto
  operacional los completan desde el workspace resuelto.
- `metodo_captura` vive tanto en evidencia como en observación y expresa el canal
  declarado por cada writer.
- No existe FK desde evidencia a workspace. `workspace_id` se conserva dentro de
  `metadata_extraccion` y metadata operacional.
- `FuenteDatos` identifica la fuente lógica y se relaciona con plantillas, procesos de
  ingesta y observaciones.
- `EvidenciaObra` representa el documento; `VersionEvidencia` fija archivo, versión y
  checksum. Observaciones, lotes, eventos materiales y entradas de cálculo pueden
  referenciarlas sin fusionar responsabilidades.
- `ProcesoIngesta` registra interpretación, contexto, clasificación, estado y
  contadores. `RegistroExtraido` conserva cada fila/registro crudo.
- `Observacion.registro_extraido` enlaza el dato confirmado con su raw input;
  `metadata_extraccion` conserva además datos sugeridos y metadata legacy.

### Inventario de caminos de captura

- **MANUAL:** `views_sector_flows_v1` y el registro manual sectorial crean evidencia
  opcional, actividad, observaciones y registro de flujo con workspace, actor y área.
- **DOCUMENT:** `ingestion_v2` crea/reutiliza evidencia y versión, analiza el documento,
  genera registros extraídos y confirma mediante handlers hacia actividad/observación.
- **TABULAR:** `ingestion_v2` lee CSV/XLSX, aplica `PlantillaMapeo`/`MapeoColumna`, crea
  raw rows y los confirma mediante los handlers operacionales.
- **API:** la ingesta estructurada sin archivo crea `ProcesoIngesta` y registros crudos,
  y reutiliza la misma confirmación gobernada.
- **TELEMETRY:** usa la ruta estructurada sin versión documental y mantiene
  `tipo_ingesta=telemetria` hasta producir observaciones.
- **SENSOR:** Ingestion admite el tipo sensor; IoT/Sensors V2 persiste lecturas y las
  proyecta a `Observacion` mediante su servicio especializado.
- **LEGACY:** views, seeds, serializers y extractores históricos escriben o consumen
  `EvidenciaObra`, `RegistroEmision`, lotes forestales y metadata de extracción sin
  pasar necesariamente por `ProcesoIngesta`.

### Gate y deuda preservada

- Tests arquitectónicos acumulados: 41/41 correctos.
- Se cubren creación, identidad, relaciones, tenant safety, constraint de versión y
  la inmutabilidad de `datos_originales` procesados.
- Ingestion V2, multisource, evidencia, registro manual y auditoría de huérfanos:
  53/53 correctos.
- Activity Core, IoT/Sensors V2, materiales, transporte, Calculation V2 y Quality V2:
  106/106 correctos.
- Contexto operacional, evidencia adicional, gobernanza, revisión profesional y flujos
  sectoriales: 68/68 correctos.
- Gate de baseline: 24 tests; 18 correctos y exactamente los seis fallos aprobados.
  `CriticalWorkScopeTests` conserva el `TypeError` de `perfil_ambiental` en
  `DocumentoAmbiental`; Construction V1 conserva `ActividadOperacional.DoesNotExist`;
  los otros cuatro corresponden al catálogo de áreas y a la columna SQLite histórica.
- No se modificaron services, views, serializers, permisos, IoT ni frontend.
- No se agregó QR ni se movieron modelos de compliance, Quality, Governance o flujos.
- Los seis fallos baseline aprobados permanecen fuera del alcance de ARQ-02G.

## ARQ-02H — Environmental Flows, Quality & Indicators

### Modelos y ownership

ARQ-02H extrae a `models/environmental_flows.py`:

- `RegistroFlujoAmbiental`

a `models/quality.py`:

- `EvaluacionCalidadDato`
- `DiscrepanciaDato`
- `PoliticaConfianzaFuente`

y a `models/indicators.py`:

- `IndicadorAmbiental`
- `ValorIndicador`
- `LineaBaseAmbiental`
- `PeriodoComparable`

No se encontró otro modelo cuya responsabilidad fuese exclusivamente flujo, calidad o
indicadores y que debiera entrar automáticamente. Governance, Calculation, Compliance
e Improvement permanecen deliberadamente fuera.

### Dependencias, schema y registry

Environmental Flows importa directamente Platform, Operational Context, Assets,
Operational Data y Materials. Quality importa Platform y Operational Data, además de
`User` de Django. Indicators importa Platform y `Obra` desde Operational Context. No
existen imports desde `models.__init__` ni ciclos nuevos.

Los ocho modelos conservan íntegramente campos, choices, defaults, relaciones,
constraints, indexes, validaciones y tablas históricas. La API pública y Django
registry comparten identidad con los owner modules. El registry permanece en 94
modelos y 94 labels únicos; no se generan migraciones.

### Consumers actuales

- `RegistroFlujoAmbiental`: **WRITE** en serializers sectoriales, registro manual e
  ingestion handlers; **READ/EVALUATE** en `sector_flows_v1`; **REPORT** en views de
  flujos; **LEGACY** en agregaciones de gestión hídrica/suelo.
- `EvaluacionCalidadDato`: **WRITE/EVALUATE** en `quality_v2`; **READ/REPORT** en views
  y serializers Quality V2; **AI** en `knowledge_v1` como señal de calidad.
- `IndicadorAmbiental`: **WRITE/READ** mediante serializers y views Quality V2;
  **REPORT** en contexto/copiloto; **EVALUATE** en servicios de indicadores y
  comparabilidad; **AI** en copilot/context gateway.
- `ValorIndicador`: **WRITE/EVALUATE** en `indicators_v2`; **READ/REPORT** en Quality
  V2; Improvement conserva snapshots separados para intervención y verificación.

### Catálogo real de flujos

| Flujo | Actividad esperada | Destinos admitidos | Especialización / cálculo / indicador | UI y evidencia E2E observada |
|---|---|---|---|---|
| Energía | `consumo_energia` | Solo sin clasificar | Agregación sectorial; sin indicador dedicado | CRUD genérico y tests sectoriales |
| Generación propia | `generacion_energia` | Solo sin clasificar | Métricas generada/autoconsumida/exportada | CRUD genérico y tests sectoriales |
| Agua | `consumo_agua` | Solo sin clasificar | Agregación sectorial; sin indicador dedicado | CRUD genérico y tests sectoriales |
| Combustible | `consumo_combustible` | Generador, maquinaria, vehículo, equipo menor, calefacción u otro | Clasificación y cálculo de combustible | Registro manual y tests de clasificación |
| Combustible estacionario | `consumo_combustible_estacionario` | Destinos de combustible | Selector gobernado de factores y cálculo | Tests sectoriales, factores y unidades |
| Combustible móvil | `consumo_combustible` | Destinos de combustible | Clasificación móvil y cálculo cuando existe factor | Tests de clasificación y cálculo |
| Residuo | `gestion_residuo` | Residuo, reutilización, reciclaje, valorización, disposición o subproducto | Puede enlazar `EventoMaterial`; balance sectorial | CRUD genérico y tests sectoriales |
| Ruido | `monitoreo_ruido` | Solo sin clasificar | Sin cálculo o indicador dedicado encontrado | Soportado por CRUD genérico y catálogo |
| Emisiones atmosféricas | `monitoreo_emisiones_atmosfericas` | Solo sin clasificar | Sin cálculo o indicador dedicado encontrado | Soportado por CRUD genérico y catálogo |
| Suelo | `gestion_suelo` | Solo sin clasificar | Sin cálculo o indicador dedicado encontrado | Soportado por CRUD genérico y catálogo |
| Gestión hídrica y suelo | `gestion_hidrica_suelo` | Solo sin clasificar | Evaluación legacy de desborde, erosión, agua y sedimentos | Consumer legacy y tests sectoriales |

Todos los flujos comparten contexto opcional de obra, unidad, proceso, activo y punto
según granularidad. Solo residuos admiten `EventoMaterial`; no se infirieron módulos,
cálculos ni indicadores que el repositorio no demuestre.

### Gate y deuda preservada

- Tests arquitectónicos acumulados: 51/51 correctos.
- Sector flows, registro manual, combustibles, unidades y Calculation V2: 103/103.
- Quality, Indicators, Improvement, Professional y Copilot: 84/84.
- Gate baseline: 24 tests; 18 correctos y exactamente los mismos seis fallos conocidos.
- `DocumentoAmbiental` conserva el `TypeError` por `perfil_ambiental`; Construction V1
  conserva `ActividadOperacional.DoesNotExist`; permanecen los tres fallos de catálogo
  de áreas y la columna SQLite histórica de `AccionAmbiental`.
- No se cambiaron clasificación, cálculo, scoring, resolución de discrepancias,
  servicios, views, serializers, permisos, IoT ni frontend.

## ARQ-02I — Governance

### Modelos y ownership

ARQ-02I extrae a `models/governance.py`, sin alterar su API pública:

- `MetodologiaAmbiental`
- `VersionMetodologia`
- `FactorAmbiental`
- `VersionFactorAmbiental`
- `FormulaAmbiental`
- `VariableFormula`
- `CompatibilidadVersionMetodologia`

`FactorEmision`, Calculation y Compliance permanecen deliberadamente fuera. El nuevo
módulo depende de Platform para `Organizacion` y de `User` de Django. No importa desde
`models.__init__` ni introduce ciclos.

También se trasladaron junto con sus owners las cuatro protecciones `pre_delete` de
versiones metodológicas activas, versiones de factor activas, fórmulas gobernadas y
variables de fórmulas gobernadas. Conservan el mismo comportamiento tanto en borrado
directo como por `QuerySet`.

### Contrato, schema y registry

Los siete modelos conservan campos, choices, defaults, relaciones, constraints,
índices, métodos, validaciones, tablas históricas y señales. La API pública reexportada,
los owner modules y Django registry comparten identidad. El registry permanece en 94
modelos y 94 labels únicos; `makemigrations --check --dry-run` no detecta cambios.

### Consumers de Governance

- **WRITE:** endpoints y serializers Calculation V2 crean metodologías, versiones,
  fórmulas y variables; `import_huellachile_factors` crea/actualiza factores y versiones.
- **READ/API:** serializers y views Calculation V2 exponen metodologías, factores,
  fórmulas, variables y sus versiones sin cambiar el contrato público.
- **SELECT:** `methodology_selector`, `fuel_factor_selector` y
  `methodology_compatibility` resuelven versiones activas, precedencia tenant/global y
  compatibilidad metodológica.
- **CALCULATE/EVALUATE:** `calculation_v2` ejecuta fórmulas gobernadas y
  `eligibility_v2` exige una versión de factor activa aplicable.
- **PROFESSIONAL:** `methodology_governance` gobierna transiciones y exige revisión
  profesional; `serializers_professional_v2` representa referencias metodológicas.
- **REPORT:** los resultados conservan sus snapshots en Calculation/Professional; no se
  encontró un writer de reportes que deba poseer modelos Governance.
- **AI:** no se encontró escritura autónoma de Governance por agentes. Los consumidores
  de IA reciben resultados/contexto derivados, no gobiernan versiones científicas.
- **LEGACY:** imports públicos desde `apps.analytics.models` permanecen soportados; no se
  redirigieron consumidores a imports internos.

### Configuración científica legacy auditada

- `FactorEmision` continúa siendo el catálogo legacy usado por admin, serializers,
  endpoints CRUD/importación y comandos de seed, limpieza y recategorización. Es un
  circuito paralelo al selector gobernado V2 y no fue migrado ni reinterpretado.
- `factor_electrico_default` y `permitir_registros_sin_factor` permanecen en
  `ConfiguracionOrganizacion`. El primero conserva configuración descriptiva legacy; el
  segundo mantiene la política de admisión de registros sin factor. Ninguno se convierte
  en una versión gobernada durante esta fase.
- `densidad_kg_m3` y `porcentaje_carbono` permanecen en especie/lote forestal y alimentan
  `forestal_carbono`, con fallback desde el lote a la especie. Son parámetros científicos
  de biomasa legacy, no factores de emisión gobernados por Calculation V2.
- La coexistencia anterior queda registrada como deuda arquitectónica explícita: puede
  competir conceptualmente con Governance, pero ARQ-02I no cambia precedencias, cálculos
  ni persistencia para resolverla implícitamente.

### Gate y deuda preservada

- Tests arquitectónicos acumulados: 59/59 correctos, incluyendo identidad pública,
  ownership, schema, constraints, creación global/tenant e inmutabilidad/borrado.
- Governance, importación HuellaChile, selectores, elegibilidad, unidades, Calculation V2
  y Professional V2: 97/97 correctos.
- Gate baseline: 24 tests; 18 correctos y exactamente los mismos seis fallos conocidos.
  Permanecen tres fallos del catálogo de áreas, la columna SQLite histórica de
  `AccionAmbiental`, el `TypeError` de `perfil_ambiental` en `DocumentoAmbiental` y
  `ActividadOperacional.DoesNotExist` en Construction V1.
- No se modificaron services, views, serializers, permisos, cálculo, frontend, modelos
  legacy ni migraciones. ARQ-02J queda fuera de este cierre.

## ARQ-02J — Environmental Calculations

### Modelos, ownership y dependencias

ARQ-02J extrae exclusivamente a `models/calculations.py`:

- `CalculoAmbiental`
- `InputCalculoAmbiental`
- `ImpactoAmbiental`

No se encontró otro modelo cuya responsabilidad fuese exclusivamente persistir una
ejecución de cálculo. `RegistroEmision` permanece como modelo legacy y
`environmental_engine.py` continúa usándolo sin cambios.

Calculations importa directamente Platform (`Organizacion`), Operational Data
(`ActividadOperacional`, `FuenteDatos`, `Observacion`), Governance
(`VersionMetodologia`, `FormulaAmbiental`, `VersionFactorAmbiental`,
`VariableFormula`) y Provenance (`EvidenciaObra`, `VersionEvidencia`). Operational Data
y Governance no importan Calculations; no se introdujeron ciclos ni imports desde
`models.__init__`.

### Contrato, schema, registry e inmutabilidad

Los tres modelos conservan campos, choices, defaults, relaciones, `related_name`,
`on_delete`, `Meta` y tablas históricas. `ImpactoAmbiental.calculo` continúa siendo
`OneToOneField`; los inputs conservan referencias exactas a observación, fuente,
evidencia y versión de evidencia.

La API pública, el owner module y Django registry comparten identidad 3/3. El registry
permanece en 94 modelos y 94 labels únicos; no se generan migraciones.

`CalculoAmbiental.save()` permanece intacto: una instancia persistida no puede
reescribirse. Un recálculo sigue siendo otro `CalculoAmbiental`, relacionado por
`recalculo_de`, con `motivo_recalculo` y una nueva `version_interna` según el servicio
existente. No se agregaron validaciones cross-tenant: estos tres modelos no tenían una
regla propia adicional que preservar.

### Result pipeline actual

- **CREA:** `calculation_v2.calculate_activity` selecciona Governance, calcula y crea
  `CalculoAmbiental` e `InputCalculoAmbiental`; `impact_v2.create_generated_impact`
  crea el `ImpactoAmbiental` uno-a-uno.
- **LEE/API:** `views_calculation_v2` y `serializers_calculation_v2` listan, detallan y
  exponen cálculos, inputs, impactos y snapshots.
- **RECALCULA:** `calculation_v2.recalculate` crea otro cálculo; Views Calculation V2 y
  `professional_v2.recalculate_for_correction` invocan ese circuito.
- **CONVIERTE EN IMPACTO:** `impact_v2` mapea `tipo_resultado` al choice de impacto y
  copia resultado, unidad, categoría y timestamp de actividad.
- **CONVIERTE EN INDICADOR:** `indicators_v2.generate_indicator_value` agrega impactos
  por tenant, periodo y, cuando aplica, obra; persiste `ValorIndicador`.
- **REPORTA:** `professional_v2` incorpora cálculos e inputs en snapshots de actividad,
  expedientes, auditoría e informes. Calculation V2 también expone comparación y
  snapshot técnico.
- **USA EN IMPROVEMENT:** problemáticas/intervenciones guardan snapshots separados;
  `professional_v2.build_dossier_references` enlaza cálculos e impactos asociados a las
  actividades del problema.
- **USA EN AI:** no se encontró un consumer de IA que cree o modifique directamente
  estos tres modelos. Copilot/agentes consumen contexto y resultados derivados mediante
  las capas de conocimiento/profesional.

### Snapshot técnico real

`calculation_v2` construye actualmente `CalculoAmbiental.snapshot_tecnico` con:

- IDs de metodología y versión metodológica;
- ID y tipo de fórmula;
- IDs de factor y versión de factor;
- valor, fuente y vigencias desde/hasta del factor;
- tipo y unidad de resultado, más `contexto_resultado`;
- razón de la decisión y candidatos con método, estado y motivos;
- por cada input: variable, clave, observación, valor/unidad original, valor/unidad
  normalizado, indicador y regla de conversión, factor de conversión, fuente, evidencia
  y versión de evidencia.

No almacena copias adicionales fuera de ese contrato. La clasificación está representada
por metodología/fórmula y la decisión/candidatos reales; no se añadió metadata inferida.

### Tipos de resultado reales

`CalculoAmbiental.tipo_resultado` y `VersionMetodologia.tipo_resultado` son `CharField`
con default `emision`, sin choices de modelo. Governance valida actualmente el conjunto:

`emision`, `reduccion`, `emision_evitada`, `remocion`, `compensacion`, `otro`.

El motor toma el tipo desde la versión metodológica. Existen pruebas reales para
`emision` y `reduccion`; los demás valores tienen validación de contexto y mapping a
Impacto, pero no se extendió ni reinterpretó su semántica.

### Gate y deuda preservada

- Tests arquitectónicos acumulados: 64/64 correctos.
- Calculation V2, combustible E2E, Governance, HuellaChile, selectores, unidades,
  Operational Data, ingestion/provenance, Quality/Indicators, Improvement, Professional
  y consumidores AI: 247/247 correctos.
- Suites legacy/reporting adicionales: 31/32; el único error es el `TypeError`
  preexistente de `DocumentoAmbiental(perfil_ambiental)`.
- Gate baseline: 24 tests; 18 correctos y exactamente los mismos seis fallos conocidos:
  tres del catálogo de áreas, columna SQLite histórica de `AccionAmbiental`, el mismo
  `TypeError` documental y `ActividadOperacional.DoesNotExist` en Construction V1.
- Se preservan como deuda `RegistroEmision` y `environmental_engine.py`, la validación de
  tipos fuera de los modelos, y la lógica de cálculo/eligibility/selectores en servicios.
- No se modificaron services, views, serializers, permisos, IoT, frontend ni legacy.
  ARQ-02K queda fuera de este cierre.

## ARQ-02K — Improvement

### Modelos, ownership y exclusiones

ARQ-02K extrae a `models/improvement.py` los once modelos que pertenecen
inequívocamente al aggregate moderno Problem → Action → Verification:

- `ProblematicaAmbiental`
- `AccionMejoraAmbiental`
- `MedicionSeguimientoAmbiental`
- `AlcanceProblematica`
- `IndicadorProblematica`
- `SnapshotIntervencion`
- `SnapshotValorIndicador`
- `ResultadoIntervencion`
- `CicloReevaluacionProblematica`
- `HistorialMetaProblematica`
- `HistorialProblematicaAmbiental`

Los dos historiales permanecen en el aggregate porque registran cambios de meta y
transiciones de la problemática canónica; uno de sus consumidores conserva lógica
legacy, pero no constituyen modelos Intelligence o Reporting.

`AccionAmbiental` permanece unmanaged/legacy en `models_acciones.py`. No se movieron
`RecomendacionAgenteAmbiental`, memorias, comandos, hitos IA, restricciones,
Professional ni Reporting.

### Dependencias, schema y registry

Improvement importa directamente Platform, Operational Context, Assets, Operational
Data, Provenance e Indicators. No requiere importar Calculations ni Environmental Flows:
el contrato real de `ProblematicaAmbiental` no tiene FK directa a cálculo o impacto.
Tampoco depende estructuralmente de Intelligence o Professional; esas capas apuntan a
Improvement desde el módulo raíz mediante la API pública.

Los once modelos conservan campos, choices, defaults, FK, relaciones inversas,
constraints, indexes, `Meta`, `clean()`, `save()` y `delete()`. La API pública, owner
module y registry comparten identidad 11/11. El registry permanece en 94 modelos y 94
labels únicos; no se generan migraciones.

### Máquinas de estado reales

**ProblematicaAmbiental** conserva estados modernos:

`detectada`, `analizando`, `propuesta`, `accion_seleccionada`, `implementando`,
`seguimiento`, `evaluando`, `escalada_profesional`, `cerrada`.

Y estados legacy simultáneos:

`en_analisis`, `accion_propuesta`, `en_implementacion`, `en_seguimiento`, `resuelta`,
`mejora_insuficiente`, `no_resuelta`, `escalada`.

`environmental_problems.ALLOWED_TRANSITIONS` implementa solo la máquina legacy, con
`resuelta` terminal. El circuito moderno `intervention_v2` asigna
`accion_seleccionada → implementando → resuelta/no_resuelta`, y escala a
`escalada_profesional` tras tres ciclos. `propuesta` y `seguimiento` también son escritos
por adaptadores de `environmental_problems`; no se encontró transición de servicio hacia
`evaluando` o `cerrada`.

**AccionMejoraAmbiental** conserva `propuesta`, `ajustada`, `seleccionada`,
`en_implementacion`, `seguimiento`, `evaluada`, `descartada`, `cancelada`.
`intervention_v2` implementa `propuesta → seleccionada → en_implementacion → evaluada`.
Copilot puede crear propuesta y seleccionar con confirmación humana. No se encontraron
transiciones especializadas para ajustada, seguimiento, descartada o cancelada; PATCH
genérico puede persistir estados admitidos.

**ResultadoIntervencion** conserva `no_implementada`, `no_viable`, `parcial`,
`implementada_sin_efecto`, `positiva`, `negativa`, `inconclusa`. No es una máquina
mutable: `evaluate_intervention` crea un resultado calculado como positiva, negativa,
parcial, sin efecto o inconclusa; no se encontró writer actual para no implementada/no
viable.

**CicloReevaluacionProblematica** no posee campo `estado`. Su estado se deriva de
`fecha_cierre`, snapshots y `resultado`; el límite actual es tres ciclos automáticos.

### Grafo de verificación real

- Problemática → Acción: **DIRECT FK**, uno-a-muchos.
- Problemática/Acción → Medición: **DIRECT FK**; acción es opcional.
- Problemática/Acción → Snapshot: **DIRECT FK**; tipo base o resultado por ciclo.
- Snapshot → valores de indicador: **DIRECT FK**; cada valor puede referenciar un
  `ValorIndicador` origen.
- Medición → Snapshot: **MISSING** como relación directa; el servicio los conecta por
  indicador, periodo y ciclo.
- Resultado → Problemática/Acción/Snapshot base/Snapshot resultado: **DIRECT FK**.
- Ciclo → Problemática/Acción/Snapshots/Resultado: **DIRECT FK**; resultado y snapshots
  pueden estar pendientes.
- Comparación before/after: **SERVICE LOOKUP** en `intervention_v2`, usando los valores
  congelados de ambos snapshots.

Los snapshots congelados y sus valores siguen siendo inmutables. No se añadió contenido
ni una regla nueva de verificación.

### Orígenes actuales de problemáticas

- **Manual — ACTIVE:** API `views_problematicas` crea la problemática y su evento de
  detección.
- **Indicador — PARTIAL:** puede vincularse mediante `IndicadorProblematica`, pero no se
  encontró creación automática desde una desviación del indicador.
- **Calculation/Impact — MISSING:** no existe FK ni writer que cree el problema desde
  esos resultados.
- **Compliance — MISSING:** no se encontró pipeline de creación hacia Improvement.
- **AI — PARTIAL:** IA recomienda/convierte acciones para una problemática existente;
  no crea la problemática.
- **Legacy Environmental Engine — LEGACY/PARTIAL:** calcula valores y agrega mediciones
  a un problema existente mediante `measure_from_engine`; no crea el problema.
- **Seeds — TEST/DEMO:** el comando histórico crea problemas y seguimientos de muestra.

### Cierre actual

La ruta legacy `evaluate_problem` exige estado `en_seguimiento` y una medición posterior;
según la comparación asigna `resuelta`, `mejora_insuficiente` o `no_resuelta`. No exige
resultado moderno ni revisión profesional.

La ruta moderna `evaluate_intervention` exige un ciclo activo, crea snapshot resultado y
`ResultadoIntervencion`; solo un resultado positivo asigna `resuelta`, los demás
`no_resuelta`. La escalada profesional requiere tres ciclos, pero el cierre positivo no
exige revisión profesional.

El endpoint PATCH de detalle usa el serializer general y puede persistir un choice como
`cerrada` sin que el modelo exija medición, resultado, evidencia o profesional. No se
encontró un servicio `close` específico ni un consumer que asigne `cerrada`. Esta brecha
queda documentada para ARQ-09; ARQ-02K no la corrige.

### Consumers y gate

- Serializers/views de problemáticas crean y leen el aggregate completo.
- `environmental_problems`, `environmental_escalation` e `intervention_v2` ejecutan las
  dos máquinas coexistentes y escriben historial.
- Copilot convierte una recomendación confirmada en acción; contexto/knowledge/AI leen
  problemáticas y resultados sin poseerlos.
- Professional referencia problemáticas/resultados, genera correcciones, expedientes,
  snapshots e informes; SaaS/Construction agregan conteos y estado abierto.
- Tests arquitectónicos acumulados: 70/70 correctos.
- Improvement, Indicators/Calculation, Professional, Intelligence/Copilot, Knowledge y
  reporting: 142/142 correctos.
- Gate baseline: 24 tests; 18 correctos y exactamente los seis fallos conocidos,
  incluida la columna SQLite legacy `analytics_accionambiental.organizacion_id`.
- No se modificaron services, views, serializers, permisos, IoT, frontend, Intelligence
  ni legacy. ARQ-02L queda fuera de este cierre.

## ARQ-02L — Intelligence

### Modelos, ownership y dependencias

ARQ-02L extrae exclusivamente a `models/intelligence.py` los siete modelos de la capa
advisory/contextual encontrados en el repositorio:

- `RecomendacionAgenteAmbiental`
- `MemoriaOrganizacion`
- `RestriccionContextual`
- `HistorialRestriccionContextual`
- `HitoDecisionIA`
- `ComandoCopiloto`
- `CasoConocimientoAmbiental`

Intelligence importa directamente Platform (`Organizacion`) e Improvement
(`ProblematicaAmbiental`, `ResultadoIntervencion`). No se movieron modelos de
Improvement, Professional o Reporting. Los dominios determinísticos no importan el
nuevo módulo para producir verdad ambiental; sus referencias inversas de Django se
mantienen sin cambios.

Las restricciones conservan ownership físico en Intelligence porque así está modelado
el aggregate actual. Su `tipo` es texto libre y puede representar responsabilidades que
en el futuro pertenezcan a Operations, Governance o Compliance; ARQ-02L no cambia ese
ownership semántico.

### Contrato, schema y registry

Los siete modelos conservan campos, choices, defaults, relaciones, `related_name`,
`on_delete`, constraints, indexes, `Meta`, validaciones y tablas históricas. La API
pública, el owner module y Django registry comparten identidad 7/7. El registry
permanece en 94 modelos y 94 labels únicos; no se generan migraciones.

Las pruebas arquitectónicas crean las siete entidades y verifican relaciones con
problemática/resultado, aislamiento tenant, historial de restricción y los estados
reales `preparado`, `confirmado` y `rechazado` de `ComandoCopiloto`.

### Contexto consumido por IA

El contexto real incluye, según el servicio y categoría solicitada:

- organización, preset, obra y alcance operacional;
- actividades y observaciones operacionales, viajes, materiales y flujos sectoriales;
- evidencias, documentos y sus estados, excluyendo archivos y texto extraído;
- indicadores, valores recientes, metas, comparaciones y snapshots de intervención;
- métricas determinísticas ya calculadas y registros de emisión validados;
- reglas normativas activas y validadas;
- problemática, acciones probadas, ciclos de reevaluación e historial resumido;
- restricciones activas, memoria organizacional vigente y conocimiento comparable;
- activos, condiciones/mantenimientos, sensores, calibración y lecturas recientes.

El Context Builder se clasifica **PARTIAL**. `CopilotProposalService` usa el
`ContextGateway` central y categorías permitidas explícitamente; el agente ambiental
usa `minimal_agent_context` en `environmental_context.py`. Knowledge arma un payload
propio desde resultados verificados. No se unificaron estos builders.

### AI write paths y autoridad

- Actividades, observaciones, cálculos, impactos, indicadores, cumplimiento, factores y
  metodologías: **NONE**; no se encontraron escrituras desde la capa IA.
- Recomendaciones, hitos y memoria contextual: **DIRECT**, limitadas a modelos
  Intelligence y sin convertir por sí mismas verdad operacional.
- Acción de mejora y selección de acción: **CONFIRMED-HUMAN / SERVICE-MEDIATED**;
  `confirm_command` crea/selecciona la acción solo después de confirmar un comando
  preparado.
- Estado de problemática y escalamiento: **AI + HUMAN / SERVICE-MEDIATED**; solo el
  comando confirmado delega en `select_action` o `escalate_problem`.
- Restricciones: **AI + HUMAN** para comandos preparados; la refutación explícita del
  usuario crea directamente una restricción y memoria, y genera una propuesta ajustada.
- Cierre, cumplimiento, factores, metodologías y reportes finales: no existe autoridad
  AI. Los cálculos son **DETERMINISTIC** y la validación/corrección final existente es
  **PROFESSIONAL**.
- Knowledge persiste casos derivados de un `ResultadoIntervencion` existente; valida
  procedencia IA/profesional cuando se declara y no recalcula el resultado.

El patrón preservado es: IA propone → comando queda preparado → humano confirma → un
servicio ejecuta la transición permitida. No existe auto-confirmación ni side effect en
`model.save()`.

### Prompts, outputs y restricciones

Los dos callers LLM reales usan `OpenAIEnvironmentalProvider`, Responses API y el modelo
`gpt-5-mini`; la clave se obtiene desde settings y no se persiste. El agente recibe
reglas de no invención/no cálculo y contexto JSON, exige JSON con diagnóstico separado
en hechos, correlaciones e hipótesis, acción, justificación, indicador, resultado,
prioridad, seguimiento y confianza. Valida campos, choices, KPI y afirmaciones de
cumplimiento/efectividad antes de persistir.

El copiloto extiende esas reglas con prohibición explícita de ejecutar o modificar
estado. Exige JSON con título, descripción, justificación, KPIs, requisitos, riesgos,
prioridad, hechos, limitaciones y supuestos; valida estructura, listas, prioridad y KPIs
asociados. No existe fallback de contenido: errores del proveedor o validación se
propagan y no persisten una propuesta válida ficticia.

La clasificación observable de restricciones es:

- `restriccion_operacional` y restricciones preparadas por comando: **OPERATIONAL**
  cuando el payload humano así lo describe; el modelo no impone taxonomía.
- `refutacion_usuario`: **AI-PREFERENCE / INTERNAL**, pues expresa feedback humano que
  condiciona la siguiente propuesta.
- cualquier otro valor libre: **UNKNOWN**. No hay choices suficientes para afirmar
  categorías ENVIRONMENTAL o REGULATORY de forma determinística.

### Gate y deuda preservada

- Tests arquitectónicos acumulados: 75/75 correctos.
- Intelligence, Improvement, Professional, Governance, Methodology, Calculation y los
  consumidores Reporting existentes: 117/117 pruebas reales correctas. Reporting no
  posee suite independiente; su cobertura está en Professional V2.
- Gate baseline: 24 tests; 18 correctos y exactamente los mismos seis fallos conocidos:
  tres del catálogo de áreas, columna SQLite histórica de `AccionAmbiental`, el
  `TypeError` de `DocumentoAmbiental(perfil_ambiental)` y
  `ActividadOperacional.DoesNotExist` en Construction V1.
- Se preservan como deuda el Context Builder parcial, el `tipo` libre de restricciones,
  la coexistencia de estados legacy/modernos de Improvement y los límites de autoridad
  ya documentados. No se modificaron prompts, providers, services, views, serializers,
  permisos, frontend ni comportamiento.
- ARQ-02L se detiene aquí; Professional y Reporting permanecen para ARQ-02M.
