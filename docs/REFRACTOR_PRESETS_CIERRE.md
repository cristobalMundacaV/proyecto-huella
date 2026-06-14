# Carbono Zero - Cierre refactor incremental nucleo + presets

## Objetivo

Preparar Carbono Zero para operar como una plataforma generica de gestion ambiental por empresa, con un nucleo comun y presets por rubro, sin romper el backend actual ni los endpoints historicos basados en constructoras.

## Logros alcanzados

- El frontend trabaja visualmente con el concepto generico de Empresa.
- Construccion queda como preset por defecto y mantiene compatibilidad con el flujo actual.
- Se agregaron presets para construccion, aserradero, transporte e industrial.
- La navegacion, labels, inteligencia operativa, dashboard, reportes, evidencias, factores e importaciones se resuelven por preset.
- Aserradero cuenta con flujo operativo real para modulos forestales.
- Transporte e industrial quedan preparados con navegacion, placeholders, factores, evidencias, reportes e importaciones base.
- El backend expone el campo `preset` en `Constructora`, sin renombrar el modelo ni cambiar endpoints.
- Las empresas existentes quedan cubiertas por fallback a `construccion`.

## Arquitectura actual

- `frontend/src/presets/registry.js` centraliza el preset activo y el fallback.
- Cada preset define configuracion de UI, navegacion, inteligencia, factores, evidencias, reportes e importaciones.
- `frontend/src/core/` contiene vistas reutilizables por preset:
  - `dashboard`
  - `evidencias`
  - `factores`
  - `importaciones`
  - `reportes`
  - `system`
- `frontend/src/features/` conserva wrappers y compatibilidad con vistas existentes.
- `frontend/src/shared/services/api.js` mantiene funciones antiguas y aliases incrementales como `getEmpresas`, `createEmpresa` y `deleteEmpresa`.

## Backend actual

- El modelo sigue llamandose `Constructora`.
- El campo `rubro` se mantiene.
- El campo `preset` fue agregado a `Constructora`.
- Los endpoints `/constructoras/` siguen vigentes.
- No se hizo renombre de base de datos.
- No se cambiaron modelos principales como `Obra`, `Etapa` o `RegistroEmision`.
- Las respuestas principales incluyen `preset` cuando corresponde.

## Compatibilidad

- No se renombro `Constructora` a `Empresa`.
- No se cambiaron endpoints backend.
- Construccion sigue siendo el preset por defecto.
- Los flujos actuales de login, empresa activa, dashboard, emisiones, evidencias, factores, reportes e importaciones de construccion conservan compatibilidad.
- El flujo completo XLSX de construccion sigue disponible en el componente existente de importacion completa.

## Presets soportados

### Construccion

- Preset por defecto.
- Mantiene obras, etapas, emisiones, evidencias, factores, importaciones y reportes.
- Usa endpoints actuales de constructoras, obras, etapas y registros.

### Aserradero / Forestal

- Cuenta con flujo operativo real.
- Modulos disponibles:
  - Recepcion de trozas
  - Produccion
  - Secado
  - Energia
  - Transporte forestal
  - Residuos / Subproductos
- Las importaciones CSV crean registros ambientales mediante el backend existente.
- La metadata preserva `preset`, `module`, `imported_from` y `original_row`.

### Transporte

- Navegacion y experiencia visual preparadas.
- Modulos preparados:
  - Flota
  - Viajes
  - Combustible
  - Rutas
  - Mantenciones
- Pendiente conectar flujo operativo backend especifico.

### Industrial

- Configuracion preparada para energia, combustible, procesos, residuos, agua, factores y evidencias.
- Pendiente conectar flujo operativo backend especifico.

## Importaciones adaptativas

- El core vive en `frontend/src/core/importaciones/`.
- Cada preset expone su configuracion en `frontend/src/presets/<preset>/import.js`.
- Construccion usa las funciones actuales de preview/confirm del backend.
- Aserradero parsea CSV en frontend, valida filas, mapea payloads a `RegistroEmision` y llama a `createEmpresaRegistroAmbiental`.
- Transporte e industrial tienen plantillas preparadas y mensajes de modulo pendiente.

## Metadata

La metadata permite conservar el origen operativo sin cambiar todavia los modelos backend:

```json
{
  "preset": "aserradero",
  "module": "secado",
  "imported_from": "preset_import",
  "original_row": 2
}
```

Este enfoque permite evolucionar a modelos especificos en fases futuras sin perder trazabilidad.

## No tocado intencionalmente

- No se renombro tabla ni modelo `Constructora`.
- No se migraron endpoints a `/empresas/`.
- No se reescribio el backend por preset.
- No se eliminaron funciones antiguas del frontend.
- No se forzo transporte o industrial a crear datos operativos reales todavia.
- No se reemplazo el flujo completo de importacion XLSX de construccion.

## Checklist QA manual

- Construccion:
  - Login funciona.
  - Empresa activa carga con preset `construccion`.
  - Sidebar muestra Empresas, Obras y Etapas.
  - Dashboard carga igual.
  - Importaciones por constructoras, factores, etapas, obras y registros siguen disponibles.

- Aserradero:
  - Empresa activa con preset `aserradero` cambia navegacion.
  - Sidebar muestra Recepcion de trozas, Produccion, Secado, Energia, Transporte forestal y Residuos / Subproductos.
  - Dashboard forestal carga.
  - Importacion CSV crea registros con metadata forestal.

- Transporte:
  - Empresa activa con preset `transporte` cambia navegacion.
  - Modulos Flota, Viajes, Combustible, Rutas y Mantenciones muestran placeholders premium.
  - Importaciones muestran plantillas preparadas sin intentar crear datos backend.

- Industrial:
  - Empresa activa con preset `industrial` usa fallback seguro.
  - Reportes, evidencias, factores e importaciones muestran configuracion preparada.
  - No se bloquea dashboard ni navegacion.

## Siguientes pasos sugeridos

- Crear endpoints `/empresas/` como alias backend cuando se decida iniciar el renombre real.
- Modelar entidades especificas por preset solo cuando exista flujo operacional validado.
- Conectar importaciones reales para transporte e industrial.
- Migrar progresivamente textos internos de `constructora` a `empresa` sin tocar la base hasta una fase dedicada.
- Agregar pruebas automatizadas de preset activo, navegacion e importaciones por preset.

## Validacion final ejecutada

Fecha de validacion: 2026-06-14.

### Comandos ejecutados

Backend:

```bash
cd backend
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
```

Frontend:

```bash
cd frontend
npm run build
npm run lint
```

### Resultado backend

- `python manage.py makemigrations --check`: OK. No se detectaron cambios de modelo pendientes de migracion.
- Migraciones presentes revisadas:
  - `0002_constructora_preset.py`
  - `0003_factoremision_activo_factoremision_metadata_and_more.py`
  - `0004_alter_factoremision_categoria.py`
- `python manage.py migrate`: bloqueado por autenticacion local de Postgres. Error: `password authentication failed for user "admin_carbono"` contra `127.0.0.1:5433`.
- `python manage.py check`: OK. `System check identified no issues`.

### Resultado frontend

- `npm run build`: OK. Vite genero build de produccion correctamente.
- Advertencia no bloqueante: chunk principal mayor a 500 kB despues de minificacion.

### Resultado lint

- `npm run lint`: OK con codigo exitoso.
- Quedan 14 warnings antiguos de dependencias de hooks (`react-hooks/exhaustive-deps`) en auth, constructoras, emisiones, mapas, registros de emision y Toast.
- No quedan errores de lint introducidos por el refactor de presets.

### Pendientes conocidos

- Corregir credenciales o disponibilidad de Postgres local para poder ejecutar `python manage.py migrate`.
- Revisar warnings historicos de hooks en una tarea separada, sin mezclarlo con el cierre de presets.
- Validar manualmente en navegador la creacion de empresas por preset y los flujos operativos descritos en la checklist QA manual.

### Decision final

El refactor incremental queda cerrado como `nucleo + presets estabilizado` a nivel de codigo y build frontend. La unica validacion bloqueada es la aplicacion local de migraciones por credenciales de base de datos, no por cambios pendientes de modelo.
