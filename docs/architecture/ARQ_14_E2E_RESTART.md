# ARQ-14 — E2E Restart

## Estado

ARQ-14 permanece **EN PROGRESO**. Este documento registra los puntos de control
ejecutados y cada `STOP` obligatorio antes de continuar con el recorrido E2E
completo.

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

La fase 1 está validada. Las fases 2 a 22 permanecen **NOT STARTED**. No se
acumularon incidencias posteriores al primer hallazgo de Checkpoint 1.

## Cambios de runtime y esquema

- Runtime: ninguno.
- APIs: sin cambios.
- Esquema/migraciones: ninguno.
- Resultados científicos: sin cambios.

## Checkpoint 1 — Fases 1–4

### Precondición PostgreSQL — incidencia encontrada

Al crear el tenant ficticio nuevo en la base local `carbono_zero`, PostgreSQL
rechazó la escritura porque `analytics_organizacion.nombre_comercial` no
existía. La auditoría de migraciones confirmó que el código no requería una
migración nueva: las migraciones existentes `0045` a `0050` estaban pendientes
en esa base.

Corrección aplicada:

```text
python backend/manage.py migrate
```

Se aplicaron correctamente:

- `0045_evidenciaobra_metodo_captura_and_more`;
- `0046_capacidadorganizacion_disponibilidad_inicial_and_more`;
- `0047_obra_contexto_operacional`;
- `0048_operational_atmospheric_emissions_and_soil`;
- `0049_alter_registroflujoambiental_destino_operacional`;
- `0050_alter_registroflujoambiental_flujo`.

No se generaron migraciones ni se modificó el esquema definido en el
repositorio; se alineó la base real con migraciones ya versionadas.

### Fase 1 — Onboarding

**Acción.** Se creó el tenant ficticio
`ARQ14 Checkpoint 1 Constructora Circular SpA`, un administrador y un tenant
ajeno de control. El administrador inició sesión mediante `/api/auth/login/` y
ejecutó por `/api/onboarding/` las cuatro etapas actuales: empresa, estructura,
aspectos ambientales y revisión final.

**Esperado.** Login y etapas HTTP exitosas; identidad chilena, nueve áreas y
diez aspectos persistidos; onboarding finalizado; un administrador de otro
tenant no puede leer el onboarding.

**Obtenido.** Login `200`, lectura inicial `200`, etapas 1–4 `200` y acceso del
tenant ajeno `404`.

**Datos persistidos.**

- organización pública:
  `ARQ14_CHECKPOINT_1_CONSTRUCTORA_CIRCULAR_SPA`;
- RUT `21.683.264-7`, país `Chile`, Región del Biobío, Concepción;
- `onboarding_step = 4` y `onboarding_completado = true`;
- nueve áreas activas;
- diez aspectos habilitados: materiales, transporte, combustibles, energía,
  agua, residuos no peligrosos, residuos peligrosos, ruido, emisiones
  atmosféricas y suelo;
- disponibilidad inicial preservada por aspecto;
- no se crearon relaciones área/aspecto implícitas no enviadas por el usuario.

Estado de la fase: **PASS después de corregir la precondición de base**.

### Fases 2–4

- Fase 2, contexto operacional: **NOT STARTED**.
- Fase 3, creación de obra: **NOT STARTED**.
- Fase 4, perfil/aplicabilidad: **NOT STARTED**.

Se aplica `STOP` después del primer defecto real encontrado y de repetir con
éxito la fase afectada. No se inició la fase 5.
