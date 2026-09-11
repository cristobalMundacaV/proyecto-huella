# Carbono Zero — Deploy, testing y operación

## URLs documentadas

- landing: `https://carbonozero.mundacasolutions.com`
- app: `https://app.carbonozero.mundacasolutions.com`

## Infraestructura

El repositorio incluye Docker, Docker Compose, Nginx, `ops/`, scripts de instalación, deploy worker y `deploy.sh`.

## Deploy

Toda modificación productiva debe pasar por código versionado. Antes de cambios: backup, comprobar estado, migraciones, build, tests, validación Nginx, health checks y rollback definido.

## Backend gate

Comandos documentados: `makemigrations --check`, `migrate`, `check`, `test`.

## Frontend gate

`npm run test`, `npm run build` y `npm run lint` cuando aplique.

## Arquitectura ARQ

Las fases ARQ recientes incluyen suites de regresión amplias para Operational Kernel, Unified Capture y Generic Environmental Engine. No usar números históricos de tests como estado presente sin ejecutar nuevamente.

## Riesgos de prueba

Prioridad máxima: cross-tenant, pérdida de procedencia, factor equivocado, duplicación, mezcla de obra, evidencia/version incorrecta, AI escribiendo verdad, cambio histórico y migración legacy.

## Base de datos

Producción debe usar PostgreSQL. El `backend/db.sqlite3` del repositorio debe tratarse como artefacto de desarrollo/demo, no como fuente productiva canónica.

## Backups

Respaldar DB, media/evidencias y configuración crítica no versionada. Probar restauración.

## Observabilidad

Monitorear backend, Nginx, DB, almacenamiento, jobs, fallos de procesamiento de evidencia, IA, sensores y errores de cálculo/importación.