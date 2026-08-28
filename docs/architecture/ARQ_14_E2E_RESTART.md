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

### Fase 2 — Contexto operacional

**Acción.** El administrador inició sesión mediante `/api/auth/login/`, consultó
`/api/contexto-operativo/espacios/` y creó dos espacios mediante el endpoint de
espacios operacionales de su membresía. Se resolvió el contexto actual primero
de forma automática y luego seleccionando explícitamente cada workspace con
`X-Workspace-ID`.

**Esperado.** Sin espacios, el endpoint declara compatibilidad legacy; con uno,
lo selecciona automáticamente; con más de uno, exige una selección real. Cada
contexto conserva rol, scope, área y tenant, y un usuario ajeno no puede resolver
el workspace.

**Obtenido.**

- login `200`;
- consulta inicial de espacios `200`, sin resultados, `legacy = true`;
- creación del primer workspace `201`;
- resolución automática con un workspace `200`;
- creación del segundo workspace `201`;
- consulta con dos workspaces `200`, `automatico = false`;
- resolución sin selección con múltiples workspaces `400` y error en
  `workspace_id`;
- selección explícita de cada workspace `200`;
- selección del workspace por un usuario de otro tenant `404`;
- el usuario ajeno obtiene cero espacios propios en este escenario.

**Datos persistidos.**

| Workspace | Área operacional | Organización | Obra | Estado |
| --- | --- | --- | --- | --- |
| Oficina técnica corporativa | Oficina técnica | `ARQ14_CHECKPOINT_1_CONSTRUCTORA_CIRCULAR_SPA` | `null` | Activo |
| Gestión ambiental corporativa | Medio ambiente / Sostenibilidad | `ARQ14_CHECKPOINT_1_CONSTRUCTORA_CIRCULAR_SPA` | `null` | Activo |

El alcance de la membresía permanece `organizacion`. `obra = null` es el scope
correcto en este punto: la Fase 3 todavía no ha creado una obra y no se fabricó
una relación anticipada para hacer pasar el checkpoint.

El contrato quedó comprobado como:

```text
Role      = admin y su conjunto de permisos
Scope     = organización; sin obra antes de Fase 3
Area      = origen operacional seleccionado
Workspace = contexto activo y seleccionable
```

Estado de la fase: **PASS**.

### Fase 3 — Creación de obra

**Acción.** El administrador inició sesión y creó por
`POST /api/organizaciones/{organizacion_id}/obras/` la obra ficticia
`Edificio Circular Los Alerces`, enviando identidad, ubicación territorial,
periodo, superficie, estado y tipo de proyecto. La petición se ejecutó desde uno
de los workspaces organizacionales existentes.

Después se validaron el listado y detalle actuales, el acceso desde ambos
workspaces organizacionales y la creación de un workspace de alcance obra
mediante el endpoint vigente de contexto operacional. No se ejecutó PATCH porque
la creación actual no lo requiere.

**Esperado.** Creación `201`, persistencia íntegra dentro del tenant, lectura
desde los contextos autorizados y ocultamiento `404` frente al tenant ajeno. La
creación de obra no debe iniciar el perfil ambiental ni decidir aplicabilidad.

**Obtenido.**

- login `200`;
- creación de obra `201`;
- listado desde cada uno de los dos workspaces existentes `200`, incluyendo la
  obra nueva;
- detalle por `codigo_obra` `200`;
- creación de workspace con scope de obra `201`;
- resolución del nuevo contexto de obra `200`;
- detalle, listado del tenant y workspace consultados por el usuario ajeno:
  `404` en los tres casos.

**Datos persistidos.**

| Campo | Valor |
| --- | --- |
| ID | `7` |
| Código | `EDIFICIO_CIRCULAR_LOS_ALERCES` |
| Organización | `ARQ14_CHECKPOINT_1_CONSTRUCTORA_CIRCULAR_SPA` |
| Nombre | Edificio Circular Los Alerces |
| Ubicación | Avenida Los Carrera 2450, acceso norte de prueba |
| Región / comuna | Región del Biobío / Concepción |
| Inicio | 2026-09-01 |
| Término estimado | 2028-03-31 |
| Superficie | 18.500,000 m² |
| Tipo de proyecto | Edificación habitacional |
| Perfil derivado | `edificacion` |
| Estado | `planificada` |
| Etapa principal | `null`, opcional y no informada |

El workspace `Oficina técnica — Los Alerces` quedó persistido con la membresía,
el área Oficina técnica y `obra_id = 7`. El contexto resuelto devuelve la misma
organización y obra.

Se confirmó además:

- cero diagnósticos ambientales asociados a la obra;
- cero aplicabilidades asociadas a la obra.

Por tanto, la Fase 4 no fue iniciada implícitamente.

Estado de la fase: **PASS**.

### Fase 4

- Perfil/aplicabilidad: **NOT STARTED**.

Se aplica `STOP` al completar la única fase autorizada por Checkpoint 3. No se
inició la Fase 4 ni la Fase 5.
