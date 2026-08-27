# INFRA-TEST-01 — PostgreSQL test parity

## Propósito

PostgreSQL es el baseline oficial del backend. SQLite sigue disponible como fallback
histórico de desarrollo, pero no representa constraints, migraciones, JSON y semántica
SQL del servidor con fidelidad suficiente para certificar la suite principal.

La infraestructura local usa exactamente `postgres:16-alpine`, en un proyecto Compose
aislado llamado `carbono-zero-tests` y un servicio dedicado `db-test`. No comparte red,
volumen ni base con producción: sus datos viven en `tmpfs` y se eliminan al destruir el
contenedor.

## Preparación

El puerto reservado es `127.0.0.1:5434` (contenedor `5432`). El puerto 5433 ya estaba
ocupado por la base local de desarrollo durante la implementación; por eso tests usa
5434 y mantiene separación física. Comprueba que esté libre si otro PostgreSQL corre
localmente.

```powershell
docker compose -f docker-compose.test.yml up -d --wait db-test
Copy-Item .env.test.example .env.test
```

`.env.test` está ignorado por Git. La plantilla contiene únicamente credenciales locales
de test y puede ajustarse si se cambia el puerto del compose.

## Ejecución segura

Desde la raíz del repositorio:

```powershell
python backend/scripts/run_tests_postgres.py
```

Para ejecutar labels concretos:

```powershell
python backend/scripts/run_tests_postgres.py apps.analytics.test_model_modularization
```

El runner carga `.env.test`, rechaza cualquier engine distinto de PostgreSQL, exige un
host loopback y una base terminada en `_test`, y bloquea nombres productivos conocidos.
Nunca imprime la contraseña. Antes de iniciar Django tests abre una conexión real y
exige:

```text
Django connection.vendor: postgresql
```

Django crea, migra y destruye `test_carbono_zero_test` normalmente. `--keepdb` no forma
parte del flujo inicial.

## Comprobación y apagado

El runner ejecuta la suite sin fallback silencioso. Para una comprobación manual con el
mismo entorno se recomienda usar el runner con un test pequeño; `manage.py check` se
valida como parte del cierre de infraestructura.

```powershell
docker compose -f docker-compose.test.yml down
```

Al usar `tmpfs` no queda volumen de datos de test persistente.

## Driver

El backend ya utiliza `psycopg[binary]>=3.2,<4` (versión runtime verificada: `3.2.9`),
el mismo driver configurado para el entorno PostgreSQL existente. INFRA-TEST-01 no
agrega ni sustituye dependencias.

## Baselines

### SQLite anterior

El gate histórico de 24 tests finalizaba 18/24. Sus seis fallos conocidos eran: tres
rechazos del catálogo legacy de áreas, ausencia de
`analytics_accionambiental.organizacion_id`, `DocumentoAmbiental(perfil_ambiental)` y
`ActividadOperacional.DoesNotExist` en Construction V1.

### PostgreSQL 16

La nueva baseline oficial ejecutó 24 tests sobre `postgres:16-alpine`: 19 correctos y
cinco fallos conocidos.

- **SAME FAILURE:**
  `SaaSOnboardingE2ETests.test_full_provision_activation_and_onboarding`, línea 84;
  `EditableOperationalStructureTests.test_matrix_is_editable_idempotent_and_tenant_safe`,
  línea 210; y
  `test_configuration_change_regenerates_diagnostic_without_obsolete_rows`, línea 220,
  mantienen `AssertionError: 400 != 200` por área no válida.
- **SAME FAILURE:**
  `CriticalWorkScopeTests.test_evidence_scope_and_role_actions`, línea 40, mantiene
  `TypeError: DocumentoAmbiental() got unexpected keyword arguments:
  'perfil_ambiental'`.
- **SAME FAILURE:**
  `ConstructionV1IntegrationTests.test_ingestion_resolves_work_into_activity`, línea
  148, mantiene `ActividadOperacional.DoesNotExist`.
- **SQLITE-ONLY:**
  `SaaSOnboardingE2ETests.test_identity_only_tenant_can_be_deleted_but_operational_tenant_cannot`
  pasa en PostgreSQL. El error SQLite por la columna
  `analytics_accionambiental.organizacion_id` no se reproduce.
- No se detectaron fallos **POSTGRES-ONLY** ni **CHANGED FAILURE**.

La suite arquitectónica ejecutó 75/75. La muestra crítica —modularización, contexto
operacional, ingestion, Calculation, Governance, Improvement, activos/sensores, calidad
e IoT— ejecutó 214/214. En todos los ciclos el runner confirmó
`connection.vendor == "postgresql"`, Django aplicó todas las migraciones y destruyó la
base temporal al terminar. `manage.py check` no reportó problemas y
`makemigrations --check --dry-run` devolvió `No changes detected` con PostgreSQL activo.

## Límites

Este correctivo no modifica lógica de negocio, modelos, migraciones, frontend, settings
productivos ni `docker-compose.yml`. Cualquier deuda funcional revelada por PostgreSQL
debe clasificarse antes de corregirse.
