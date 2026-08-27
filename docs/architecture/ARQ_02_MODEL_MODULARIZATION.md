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
