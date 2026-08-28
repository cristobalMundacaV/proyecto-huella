# ARQ-14 — E2E Restart

## Estado

ARQ-14 permanece **EN PROGRESO**. Este documento registra el primer punto de
control solicitado y el `STOP` obligatorio antes de continuar con el recorrido
E2E completo.

PostgreSQL es la única baseline oficial de esta fase.

## Punto de control 0 — Construction Ingestion

### Acción realizada

Se reprodujo de forma aislada
`ConstructionV1IntegrationTests.test_ingestion_resolves_work_into_activity` y
se inspeccionó el flujo HTTP completo:

```text
recibir → analizar → mapear → preview → confirmar
```

También se contrastó el escenario con los contratos cerrados de Operational
Kernel, Unified Capture e Ingestion/RBAC.

### Resultado esperado

Un actor autorizado confirma una ingesta API cuya fila identifica una obra por
`codigo_obra`; la confirmación crea una `ActividadOperacional` asociada a esa
obra y observaciones con provenance del proceso de ingesta.

### Resultado obtenido inicialmente

La resolución de obra y el preview eran correctos, pero la petición de
confirmación devolvía `404 {"detail": "Recurso no encontrado."}`. El test no
verificaba esa respuesta y terminaba reportando de forma secundaria que la
actividad no existía.

### Diagnóstico contractual

No era un bug de Construction Ingestion. El fixture estaba obsoleto respecto
del contrato RBAC actual:

- `UsuarioOrganizacion` usa `analista` como rol por defecto;
- `analista` puede crear y revisar importaciones, pero no posee
  `imports.confirm`;
- la confirmación requiere `Permission.IMPORT_CONFIRM`;
- la API preserva el recurso mediante `404` cuando el actor carece de ese
  permiso;
- los roles `admin`, `responsable_ambiental` y `revisor_ambiental` sí pueden
  confirmar.

Cambiar el runtime para aceptar la confirmación habría debilitado RBAC y
contradicho contratos ya cerrados. Se corrigió únicamente el escenario de
prueba para ejecutar la operación con un administrador.

### Corrección

- El fixture Construction V1 declara explícitamente el rol `ADMIN`.
- El test verifica ahora el status del mapeo y de la confirmación.
- El test verifica `filas_con_error == 0` y
  `actividades_creadas == 1` antes de consultar la actividad.

Así, un rechazo de permisos o un error de procesamiento queda señalado en la
etapa real donde ocurre y no como una falsa ausencia del hecho operacional.

### Repetición de la fase

Con un actor autorizado:

```text
obra por codigo_obra
→ preview válido
→ confirmación 200
→ una actividad creada, sin filas con error
→ ActividadOperacional.obra == obra esperada
```

Estado: **PASS**.

### Validación ejecutada

- Caso aislado prioritario: `1/1 PASS` en PostgreSQL.
- Construction + Ingestion + tenant/RBAC relacionados: `33/33 PASS` en
  PostgreSQL.
- Baseline backend completa: `584/584 PASS` en PostgreSQL.
- `manage.py check`: PASS, sin incidencias.
- `makemigrations --check --dry-run`: PASS, sin cambios de esquema.
- `compileall`: PASS.
- `git diff --check`: PASS.

## Fases E2E restantes

Las fases 1 a 22 permanecen **NOT STARTED**. No se avanzó al onboarding ni se
acumularon incidencias posteriores, respetando el `STOP` del primer hallazgo.

## Cambios de runtime y esquema

- Runtime: ninguno.
- APIs: sin cambios.
- Esquema/migraciones: ninguno.
- Resultados científicos: sin cambios.
