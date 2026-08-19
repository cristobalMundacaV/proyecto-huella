# Carbono Zero — Contrato funcional Frontend ↔ Backend

## 0. Propósito

Este documento es el inventario maestro de capacidades funcionales de Carbono Zero y el contrato de exposición del backend hacia la experiencia de usuario.

**Base auditada**
- Repositorio: `cristobalMundacaV/proyecto-huella`
- Rama: `main`
- Commit de referencia: `1a3f40d15106f27839a74efd3ab21f22f02013f8`
- Backend principal: `backend/apps/analytics/urls.py`
- Backend IoT: `backend/apps/iot/urls.py`
- Router frontend: `frontend/src/app/router/router.jsx`

## 1. Estados

- **EXPUESTO**: la capacidad está disponible desde una pantalla o flujo funcional.
- **PARCIAL**: existe pantalla o cliente API, pero el flujo no cubre todo lo que soporta el backend.
- **NO_EXPUESTO**: backend disponible sin flujo de usuario equivalente.
- **ADMINISTRATIVO**: capacidad válida pero fuera del flujo operacional principal.
- **REVISAR**: sólo se permite temporalmente mientras exista una duda de contrato; no puede quedar ningún REVISAR al cerrar esta fase.

## 2. Dueños visuales

- **GLOBAL**
- **OBRA**
- **DOMINIO**
- **PROBLEMA**
- **EVIDENCIA**
- **SENSOR**
- **GOBERNANZA**
- **ADMINISTRACION**

## 3. Regla de destino

Una capacidad no se considera resuelta porque exista un endpoint o un archivo `api.js`. Debe existir una decisión explícita de producto:

`Backend capability → Frontend flow → Pantalla → Acción → Estado → Evidencia de prueba`

---

# A. CONTEXTO, ORGANIZACIÓN Y FUNDACIÓN

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Organización | Listar organizaciones | GET | `/organizaciones/` | EXPUESTO | organizaciones | ADMINISTRACION | Seleccionar organización |
| Organización | Crear organización | POST | `/organizaciones/` | EXPUESTO | organizaciones | ADMINISTRACION | Crear organización |
| Organización | Detalle seguro | GET/PATCH/DELETE | `/organizaciones/:org/` | PARCIAL | organizaciones/configuración | ADMINISTRACION | Consultar/editar organización; eliminación sólo administrativa |
| Capacidades | Catálogo ambiental | GET | `/capacidades-ambientales/` | PARCIAL | diagnóstico | ADMINISTRACION | Conocer capacidades disponibles |
| Capacidades | Capacidades de organización | GET | `/organizaciones/:org/capacidades-ambientales/` | EXPUESTO | diagnosticoApi | ADMINISTRACION | Configurar capacidades |
| Capacidades | Modificar capacidad | PATCH | `/organizaciones/:org/capacidades-ambientales/:id/` | EXPUESTO | diagnosticoApi | ADMINISTRACION | Activar/configurar capacidad |
| Diagnóstico | Consultar diagnóstico | GET | `/organizaciones/:org/diagnostico-ambiental/?obra=:obra` | PARCIAL | diagnosticoApi | OBRA | Consultar diagnóstico de la obra |
| Diagnóstico | Crear diagnóstico | POST | `/organizaciones/:org/diagnostico-ambiental/` | PARCIAL | diagnosticoApi | OBRA | Completar diagnóstico dentro de la obra |
| Diagnóstico | Editar diagnóstico | PATCH | `/organizaciones/:org/diagnostico-ambiental/` | PARCIAL | diagnosticoApi | OBRA | Resolver aplicabilidad sin salir de la obra |
| Estructura | Listar unidades | GET | `/organizaciones/:org/unidades-operacionales/` | EXPUESTO | diagnostico/estructura | ADMINISTRACION | Ver unidades |
| Estructura | Crear unidad | POST | `/organizaciones/:org/unidades-operacionales/` | EXPUESTO | diagnosticoApi | ADMINISTRACION | Crear unidad |
| Estructura | Editar unidad | PATCH | `/organizaciones/:org/unidades-operacionales/:id/` | PARCIAL | sin flujo claro de edición | ADMINISTRACION | Editar unidad |
| Estructura | Listar procesos | GET | `/organizaciones/:org/procesos-operacionales/` | EXPUESTO | diagnostico/estructura | ADMINISTRACION | Ver procesos |
| Estructura | Crear proceso | POST | `/organizaciones/:org/procesos-operacionales/` | EXPUESTO | diagnosticoApi | ADMINISTRACION | Crear proceso |
| Estructura | Editar proceso | PATCH | `/organizaciones/:org/procesos-operacionales/:id/` | PARCIAL | sin flujo claro de edición | ADMINISTRACION | Editar proceso |
| Preparación | Resumen preparación ambiental | GET | `/organizaciones/:org/preparacion-ambiental/` | EXPUESTO | diagnosticoApi | OBRA | Mostrar cobertura ambiental viva |

---

# B. OBRA COMO UNIVERSO OPERACIONAL

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Obra | Listar/gestionar obras por organización | GET/POST | `/organizaciones/:org/obras/` | EXPUESTO | ObrasPage / obrasApi | GLOBAL | Seleccionar/crear obra |
| Obra | Contexto ambiental | GET/POST | `/organizaciones/:org/obras/:obra/ambiental/` | PARCIAL | workspaceApi | OBRA | Leer contexto y cerrar obra ambientalmente |
| Obra | Contexto operativo | GET | `/organizaciones/:org/obras/:obra/contexto/` | EXPUESTO | workspaceApi | OBRA | Mantener contexto de obra |
| Obra | Timeline | GET | `/organizaciones/:org/obras/:obra/timeline/` | EXPUESTO | ObraTimelinePage | OBRA | Reconstruir historial |
| Obra | Indicadores | GET | `/organizaciones/:org/obras/:obra/indicadores/` | EXPUESTO | ObraIndicatorsPage | OBRA | Lectura agregada de indicadores |
| Obra | Materiales | GET | `/organizaciones/:org/obras/:obra/materiales/` | EXPUESTO | operationApi | DOMINIO | Resumen de materiales de la obra |

**Decisión final:** todo flujo ambiental operativo debe poder ejecutarse sin perder `obraId`.

---

# C. FUENTES, ACTIVIDADES Y OBSERVACIONES

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Fuentes | Listar fuentes | GET | `/organizaciones/:org/fuentes-datos/` | NO_EXPUESTO | sin workspace dedicado | EVIDENCIA | Elegir origen del dato |
| Fuentes | Crear fuente | POST | `/organizaciones/:org/fuentes-datos/` | NO_EXPUESTO | — | EVIDENCIA | Crear fuente durante captura/importación |
| Fuentes | Ver fuente | GET | `/organizaciones/:org/fuentes-datos/:id/` | NO_EXPUESTO | — | EVIDENCIA | Inspeccionar procedencia |
| Fuentes | Editar fuente | PATCH | `/organizaciones/:org/fuentes-datos/:id/` | NO_EXPUESTO | — | EVIDENCIA | Corregir metadatos de fuente |
| Actividad | Listar actividades | GET | `/organizaciones/:org/actividades-operacionales/` | PARCIAL | consumidas indirectamente | OBRA | Consultar actividad real |
| Actividad | Crear actividad | POST | `/organizaciones/:org/actividades-operacionales/` | NO_EXPUESTO | — | DOMINIO | Registrar actividad |
| Actividad | Detalle | GET | `/organizaciones/:org/actividades-operacionales/:id/` | NO_EXPUESTO | — | DOMINIO | Abrir actividad y trazabilidad |
| Actividad | Editar | PATCH | `/organizaciones/:org/actividades-operacionales/:id/` | NO_EXPUESTO | — | DOMINIO | Corregir contexto operacional |
| Observación | Listar por actividad | GET | `/organizaciones/:org/actividades-operacionales/:id/observaciones/` | PARCIAL | datos visibles indirectamente | DOMINIO | Ver datos que sustentan actividad |
| Observación | Crear | POST | `/organizaciones/:org/actividades-operacionales/:id/observaciones/` | PARCIAL | creación encapsulada en otros flujos | DOMINIO | Capturar dato con fuente/evidencia |
| Observación | Detalle | GET | `/organizaciones/:org/observaciones/:id/` | NO_EXPUESTO | — | DOMINIO | Inspeccionar dato |
| Observación | Editar | PATCH | `/organizaciones/:org/observaciones/:id/` | NO_EXPUESTO | — | DOMINIO | Corregir observación sin perder identidad |

**Decisión final:** la actividad y observación no necesitan convertirse en módulos de navegación; deben ser el sustrato trazable de cada dominio.

---

# D. EVIDENCIAS E IMPORTACIONES

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Evidencia | Listar evidencia organización | GET | `/organizaciones/:org/evidencias/` | EXPUESTO | dataApi / EvidencePage | EVIDENCIA | Consultar documentos |
| Evidencia | Subir evidencia | POST | `/organizaciones/:org/evidencias/` | EXPUESTO | dataApi / EvidencePage | EVIDENCIA | Subir respaldo |
| Evidencia | Evidencia por obra legacy | GET/POST | `/obras/:codigo/evidencias/` | EXPUESTO | dataApi | OBRA | Cargar evidencia de obra |
| Evidencia | Contexto trazable | GET | `/context/evidence/:id/` | EXPUESTO | dataApi / EvidenceDetail | EVIDENCIA | Ver relaciones de evidencia |
| Evidencia | Extraer información de archivo | POST | `/organizaciones/:org/evidencias/extraer/` | NO_EXPUESTO | backend disponible; dataApi no lo expone | EVIDENCIA | Preanalizar documento antes de registrar/ingestar |
| Ingesta | Listar procesos | GET | `/organizaciones/:org/ingestas/` | EXPUESTO | dataApi / ImportsPage | EVIDENCIA | Ver importaciones |
| Ingesta | Crear proceso | POST | `/organizaciones/:org/ingestas/` | EXPUESTO | dataApi | EVIDENCIA | Subir archivo o payload estructurado |
| Ingesta | Detalle | GET | `/organizaciones/:org/ingestas/:id/` | EXPUESTO | dataApi / ImportDetailPage | EVIDENCIA | Ver estado |
| Ingesta | Analizar | POST | `/organizaciones/:org/ingestas/:id/analizar/` | EXPUESTO | dataApi | EVIDENCIA | Analizar |
| Ingesta | Guardar mapeo | POST/PATCH | `/organizaciones/:org/ingestas/:id/mapeo/` | PARCIAL | dataApi usa POST | EVIDENCIA | Mapear campos |
| Ingesta | Preview | GET | `/organizaciones/:org/ingestas/:id/preview/` | EXPUESTO | dataApi | EVIDENCIA | Revisar antes de confirmar |
| Ingesta | Confirmar | POST | `/organizaciones/:org/ingestas/:id/confirmar/` | EXPUESTO | dataApi | EVIDENCIA | Crear datos operacionales |
| Ingesta | Plantillas | GET | `/organizaciones/:org/plantillas-mapeo/` | NO_EXPUESTO | — | EVIDENCIA | Reutilizar mapeos |

**Gate posterior:** importación confirmada debe desembarcar en el dominio correspondiente y navegar de vuelta al documento original.

---

# E. ACTIVOS Y MANTENIMIENTO

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Activos | Listar | GET | `/organizaciones/:org/activos/` | EXPUESTO | assetsApi / ActivosPage | GLOBAL | Inventario operacional |
| Activos | Crear | POST | `/organizaciones/:org/activos/` | EXPUESTO | assetsApi | GLOBAL | Crear activo |
| Activos | Detalle | GET | `/organizaciones/:org/activos/:id/` | PARCIAL | página principal, sin detalle dedicado | GLOBAL | Inspeccionar activo |
| Activos | Editar | PATCH | `/organizaciones/:org/activos/:id/` | EXPUESTO | assetsApi | GLOBAL | Editar |
| Mantenimiento | Listar | GET | `/organizaciones/:org/activos/:id/mantenimientos/` | PARCIAL | backend disponible; API frontend sólo crea | GLOBAL | Ver historial mantenimiento |
| Mantenimiento | Crear | POST | `/organizaciones/:org/activos/:id/mantenimientos/` | EXPUESTO | assetsApi | GLOBAL | Registrar mantención |
| Mantenimiento | Detalle | GET | `/organizaciones/:org/mantenimientos/:id/` | NO_EXPUESTO | — | GLOBAL | Ver mantención |
| Mantenimiento | Editar | PATCH | `/organizaciones/:org/mantenimientos/:id/` | NO_EXPUESTO | — | GLOBAL | Actualizar mantención |
| Condición | Listar | GET | `/organizaciones/:org/activos/:id/condiciones/` | PARCIAL | backend disponible | GLOBAL | Ver variables operacionales |
| Condición | Crear | POST | `/organizaciones/:org/activos/:id/condiciones/` | EXPUESTO | assetsApi | GLOBAL | Registrar condición |

**Decisión final:** activos se administran globalmente y se contextualizan en Energía, Combustibles, Transporte, Ruido y Problemas.

---

# F. SENSORES E IOT V2

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Sensores | Listar | GET | `/organizaciones/:org/sensores/` | EXPUESTO | sensorsApi / SensoresPage | SENSOR | Inventario |
| Sensores | Crear | POST | `/organizaciones/:org/sensores/` | EXPUESTO | sensorsApi | SENSOR | Registrar dispositivo |
| Sensores | Detalle | GET | `/organizaciones/:org/sensores/:id/` | EXPUESTO | SensorDetailPage | SENSOR | Ver sensor |
| Sensores | Editar | PATCH | `/organizaciones/:org/sensores/:id/` | PARCIAL | depende de UI actual | SENSOR | Editar estado/configuración |
| Instalaciones | Listar | GET | `/organizaciones/:org/sensores/:id/instalaciones/` | EXPUESTO | SensorDetailPage | SENSOR | Historial instalación |
| Instalaciones | Crear | POST | `/organizaciones/:org/sensores/:id/instalaciones/` | EXPUESTO | sensorsApi | SENSOR | Registrar instalación |
| Calibraciones | Listar | GET | `/organizaciones/:org/sensores/:id/calibraciones/` | EXPUESTO | SensorDetailPage | SENSOR | Historial calibración |
| Calibraciones | Crear | POST | `/organizaciones/:org/sensores/:id/calibraciones/` | EXPUESTO | sensorsApi | SENSOR | Registrar calibración |
| Lecturas V2 | Listar | GET | `/organizaciones/:org/sensores/:id/lecturas/` | EXPUESTO | SensorDetailPage | SENSOR | Ver lecturas |
| Lecturas V2 | Crear | POST | `/organizaciones/:org/sensores/:id/lecturas/` | PARCIAL | ingestión/flujo sensor | SENSOR | Ingresar lectura controlada |

**Decisión final:** Sensor → LecturaSensorV2 → Observación → Dominio → Cálculo gobernado. Nunca sensor → CO2e directo.

---

# G. FLUJOS AMBIENTALES GENÉRICOS

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Puntos ambientales | Listar | GET | `/organizaciones/:org/puntos-ambientales/?obra=:obra` | PARCIAL | operationApi / sectorFlowsApi | DOMINIO | Ver puntos |
| Puntos ambientales | Crear | POST | `/organizaciones/:org/puntos-ambientales/` | NO_EXPUESTO | sectorFlowsApi creado, sin UI | DOMINIO | Crear punto desde dominio |
| Flujo | Listar registros | GET | `/organizaciones/:org/flujos-ambientales/?obra=:obra` | PARCIAL | operationApi / sectorFlowsApi | DOMINIO | Ver registros |
| Flujo | Crear registro | POST | `/organizaciones/:org/flujos-ambientales/` | NO_EXPUESTO | sectorFlowsApi creado, sin UI | DOMINIO | Registrar consumo/medición/condición |
| Flujo | Detalle | GET | `/organizaciones/:org/flujos-ambientales/:id/` | NO_EXPUESTO | sectorFlowsApi creado | DOMINIO | Ver registro y observaciones |
| Flujo | Editar | PATCH | `/organizaciones/:org/flujos-ambientales/:id/` | NO_EXPUESTO | sectorFlowsApi creado | DOMINIO | Corregir registro |
| Flujo | Indicadores | GET | `/organizaciones/:org/flujos-ambientales/indicadores/` | PARCIAL | sectorFlowsApi creado | DOMINIO | Resumen por flujo |

**Dueños:** Energía, Agua, Combustibles, Residuos, Ruido, Hídrica/Suelo.

---

# H. TRANSPORTE V2

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Rutas | Listar | GET | `/organizaciones/:org/rutas-operacionales/` | NO_EXPUESTO | transportApi creado | DOMINIO | Ver rutas |
| Rutas | Crear | POST | `/organizaciones/:org/rutas-operacionales/` | NO_EXPUESTO | transportApi creado | DOMINIO | Crear ruta |
| Viajes | Listar | GET | `/organizaciones/:org/viajes-operacionales/?obra=:obra` | PARCIAL | operationApi / transportApi | DOMINIO | Ver viajes |
| Viajes | Crear | POST | `/organizaciones/:org/viajes-operacionales/` | NO_EXPUESTO | transportApi creado | DOMINIO | Registrar viaje |
| Viajes | Detalle | GET | `/organizaciones/:org/viajes-operacionales/:id/` | NO_EXPUESTO | transportApi creado | DOMINIO | Auditar viaje |
| Viajes | Editar | PATCH | `/organizaciones/:org/viajes-operacionales/:id/` | NO_EXPUESTO | transportApi creado | DOMINIO | Corregir viaje |
| Transporte | Indicadores | GET | `/organizaciones/:org/viajes-operacionales/indicadores/?obra=:obra` | EXPUESTO | TransportPage | DOMINIO | Viajes/km/carga/trabajo/combustible |

---

# I. MATERIALES V2

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Material | Listar | GET | `/organizaciones/:org/materiales-operacionales/` | PARCIAL | materialsApi creado; lectura de obra por operationApi | DOMINIO | Catálogo materiales |
| Material | Crear | POST | `/organizaciones/:org/materiales-operacionales/` | NO_EXPUESTO | materialsApi | DOMINIO | Registrar material |
| Material | Detalle | GET | `/organizaciones/:org/materiales-operacionales/:id/` | NO_EXPUESTO | materialsApi | DOMINIO | Ver material |
| Material | Editar | PATCH | `/organizaciones/:org/materiales-operacionales/:id/` | NO_EXPUESTO | materialsApi | DOMINIO | Editar |
| Material | Indicadores | GET | `/organizaciones/:org/materiales-operacionales/indicadores/` | PARCIAL | materialsApi | DOMINIO | Estado agregado |
| Lotes | Listar | GET | `/organizaciones/:org/lotes-materiales/` | NO_EXPUESTO | materialsApi | DOMINIO | Ver lotes |
| Lotes | Crear | POST | `/organizaciones/:org/lotes-materiales/` | NO_EXPUESTO | materialsApi | DOMINIO | Crear lote |
| Eventos | Listar | GET | `/organizaciones/:org/eventos-materiales/?obra=:obra` | PARCIAL | operationApi / materialsApi | DOMINIO | Movimientos |
| Eventos | Crear | POST | `/organizaciones/:org/eventos-materiales/` | NO_EXPUESTO | materialsApi | DOMINIO | Entrada/uso/reuso/salida/residuo |
| Evento | Detalle | GET | `/organizaciones/:org/eventos-materiales/:id/` | NO_EXPUESTO | materialsApi | DOMINIO | Auditar movimiento |
| Evento | Editar | PATCH | `/organizaciones/:org/eventos-materiales/:id/` | NO_EXPUESTO | materialsApi | DOMINIO | Corregir movimiento |
| Balance | Consultar | GET | `/organizaciones/:org/materiales-operacionales/:id/balance/` | NO_EXPUESTO | materialsApi | DOMINIO | Entró→usado→reutilizado→residuo→saldo |
| Lineage | Consultar | GET | `/organizaciones/:org/materiales-operacionales/:id/lineage/` | NO_EXPUESTO | materialsApi | DOMINIO | Reconstruir origen/destino |

---

# J. CÁLCULO, METODOLOGÍAS E IMPACTOS

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Metodologías | Listar | GET | `/organizaciones/:org/metodologias/` | PARCIAL | calculationV2Api / gobernanza | GOBERNANZA | Catálogo metodológico |
| Metodologías | Ver | GET | `/organizaciones/:org/metodologias/:id/` | PARCIAL | calculationV2Api | GOBERNANZA | Inspeccionar versiones |
| Metodologías | Crear nueva versión | POST | `/organizaciones/:org/metodologias/:id/` | PARCIAL | gobernanza | GOBERNANZA | Versionar metodología |
| Metodología | Transición de versión | POST | `/organizaciones/:org/metodologias/:id/versiones/:version/transicion/` | PARCIAL | gobernanza | GOBERNANZA | Borrador/revisión/activa/etc. |
| Variables fórmula | Crear | POST | `/organizaciones/:org/metodologias/:id/versiones/:version/variables/` | PARCIAL | gobernanza | GOBERNANZA | Definir variable |
| Variables fórmula | Editar | PATCH | `/organizaciones/:org/metodologias/:id/versiones/:version/variables/:variable/` | PARCIAL | gobernanza | GOBERNANZA | Editar variable |
| Variables fórmula | Eliminar | DELETE | `/organizaciones/:org/metodologias/:id/versiones/:version/variables/:variable/` | PARCIAL | gobernanza | GOBERNANZA | Eliminar variable |
| Factores ambientales | Listar | GET | `/organizaciones/:org/factores-ambientales/` | EXPUESTO | FactoresPage / calculationV2Api | GOBERNANZA | Catálogo gobernado |
| Elegibilidad | Evaluar actividad | GET | `/organizaciones/:org/actividades-operacionales/:id/elegibilidad/` | PARCIAL | calculationV2Api | DOMINIO | Saber si puede calcularse |
| Cálculo | Calcular actividad | POST | `/organizaciones/:org/actividades-operacionales/:id/calcular/` | PARCIAL | calculationV2Api | DOMINIO | Ejecutar motor determinista |
| Cálculo | Listar por actividad | GET | `/organizaciones/:org/actividades-operacionales/:id/calculos/` | PARCIAL | calculationV2Api | DOMINIO | Historial de cálculo |
| Cálculo | Detalle | GET | `/organizaciones/:org/calculos/:id/` | NO_EXPUESTO | calculationV2Api | DOMINIO | Ver fórmula/factor/inputs |
| Cálculo | Recalcular | POST | `/organizaciones/:org/calculos/:id/recalcular/` | NO_EXPUESTO | calculationV2Api | GOBERNANZA | Recalcular con motivo |
| Cálculo | Snapshot | GET | `/organizaciones/:org/calculos/:id/snapshot/` | NO_EXPUESTO | calculationV2Api | GOBERNANZA | Auditar cálculo |
| Cálculo | Comparar | GET | `/organizaciones/:org/calculos/:id/comparar/:other/` | NO_EXPUESTO | calculationV2Api | GOBERNANZA | Comparar versiones |
| Impactos | Listar | GET | `/organizaciones/:org/impactos-ambientales/` | PARCIAL | inteligencia/operación | OBRA | Mostrar impactos calculados |

---

# K. CALIDAD, DISCREPANCIAS, INDICADORES Y LÍNEA BASE

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Calidad | Evaluar/listar observaciones | GET | `/organizaciones/:org/calidad/observaciones/` | EXPUESTO | QualityGovernancePage | GOBERNANZA | Ver calidad |
| Discrepancias | Listar | GET | `/organizaciones/:org/discrepancias/` | EXPUESTO | QualityGovernancePage | GOBERNANZA | Ver conflictos |
| Discrepancias | Resolver/editar | PATCH | `/organizaciones/:org/discrepancias/:id/` | PARCIAL | gobernanza | GOBERNANZA | Resolver discrepancia |
| Políticas fuente | Listar | GET | `/organizaciones/:org/politicas-fuente/` | EXPUESTO | QualityGovernancePage | GOBERNANZA | Entender confianza |
| Indicadores | Listar | GET | `/organizaciones/:org/indicadores/` | EXPUESTO | indicadores/gobernanza | OBRA | Indicadores ambientales |
| Indicadores | Serie | GET | `/organizaciones/:org/indicadores/:id/serie/` | PARCIAL | vistas analíticas | OBRA | Evolución temporal |
| Indicadores | Comparación | GET | `/organizaciones/:org/indicadores/:id/comparacion/` | PARCIAL | vistas analíticas | OBRA | Comparar periodos |
| Línea base | Listar | GET | `/organizaciones/:org/lineas-base/` | PARCIAL | gobernanza/inteligencia | OBRA | Ver líneas base |
| Línea base | Construir | POST | `/organizaciones/:org/lineas-base/` | PARCIAL | — | GOBERNANZA | Construir baseline |
| Resumen ambiental | Obtener | GET | `/organizaciones/:org/resumen-ambiental-v2/` | PARCIAL | intelligence/dashboard | OBRA | Resumen con calidad |

---

# L. PROBLEMAS Y MEJORA CONTINUA

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Problemas | Listar | GET | `/organizaciones/:org/problematicas/?obra=:obra` | EXPUESTO | ProblemsPage / improvementApi | PROBLEMA | Ver problemas |
| Problemas | Crear | POST | `/organizaciones/:org/problematicas/` | EXPUESTO | ProblemsPage | PROBLEMA | Detectar/registrar |
| Problemas | Detalle | GET | `/organizaciones/:org/problematicas/:id/?obra=:obra` | EXPUESTO | ProblemDetailPage | PROBLEMA | Workspace de resolución |
| Problemas | Editar | PATCH | `/organizaciones/:org/problematicas/:id/` | PARCIAL | API backend; UI no cubre todo | PROBLEMA | Ajustar datos |
| Problemas | Eliminar | DELETE | `/organizaciones/:org/problematicas/:id/` | PARCIAL | controlado | PROBLEMA | Eliminación excepcional |
| Problemas | Transición | POST | `/organizaciones/:org/problematicas/:id/transicion/` | PARCIAL | workflow | PROBLEMA | Cambiar estado válido |
| Alcance | Listar | GET | `/organizaciones/:org/problematicas/:id/alcance/` | EXPUESTO | improvementApi | PROBLEMA | Ver alcance |
| Alcance | Crear | POST | `/organizaciones/:org/problematicas/:id/alcance/` | PARCIAL | falta acción completa | PROBLEMA | Vincular dominio/activo/etc. |
| Indicadores problema | Listar | GET | `/organizaciones/:org/problematicas/:id/indicadores/` | EXPUESTO | improvementApi | PROBLEMA | Ver indicadores vinculados |
| Indicadores problema | Crear vínculo | POST | `/organizaciones/:org/problematicas/:id/indicadores/` | PARCIAL | falta UI completa | PROBLEMA | Añadir indicador |
| Acciones | Listar | GET | `/organizaciones/:org/problematicas/:id/acciones/` | EXPUESTO | improvementApi | PROBLEMA | Ver opciones |
| Acciones | Crear/proponer | POST | `/organizaciones/:org/problematicas/:id/acciones/` | EXPUESTO | improvementApi | PROBLEMA | Proponer acción |
| Acciones | Seleccionar | POST | `/organizaciones/:org/problematicas/:id/acciones/:action/seleccionar/` | EXPUESTO | improvementApi | PROBLEMA | Elegir intervención |
| Acciones | Iniciar | POST | `/organizaciones/:org/problematicas/:id/acciones/:action/iniciar/` | EXPUESTO | improvementApi | PROBLEMA | Iniciar con confirmación |
| Acciones | Implementar | POST | `/organizaciones/:org/problematicas/:id/acciones/:action/implementar/` | EXPUESTO | improvementApi | PROBLEMA | Marcar implementación |
| Seguimiento | Listar | GET | `/organizaciones/:org/problematicas/:id/seguimientos/` | EXPUESTO | improvementApi | PROBLEMA | Ver mediciones |
| Seguimiento | Crear | POST | `/organizaciones/:org/problematicas/:id/seguimientos/` | EXPUESTO | improvementApi | PROBLEMA | Medir resultado |
| Seguimiento | Desde motor | POST | `/organizaciones/:org/problematicas/:id/seguimientos/motor/` | EXPUESTO | improvementApi | PROBLEMA | Medición gobernada |
| Evaluación | Evaluar | POST | `/organizaciones/:org/problematicas/:id/evaluar/` | EXPUESTO | improvementApi | PROBLEMA | Determinar resultado |
| Snapshot | Base | GET | `/organizaciones/:org/problematicas/:id/snapshot-base/` | EXPUESTO | improvementApi | PROBLEMA | Comparación pre/post |
| Ciclos | Listar | GET | `/organizaciones/:org/problematicas/:id/ciclos/` | EXPUESTO | improvementApi | PROBLEMA | Historial de intervención |
| Reevaluación | Crear nuevo ciclo | POST | `/organizaciones/:org/problematicas/:id/reevaluar/` | EXPUESTO | improvementApi | PROBLEMA | Intentar otra acción |
| Escalamiento | Escalar | POST | `/organizaciones/:org/problematicas/:id/escalar/` | EXPUESTO | improvementApi | PROBLEMA | Llevar a profesional |
| Historial | Consultar | GET | `/organizaciones/:org/problematicas/:id/historial/` | EXPUESTO | improvementApi | PROBLEMA | Trazabilidad |

---

# M. CONTEXTO PREPROCESADO E INTELIGENCIA

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Contexto | Organización | GET | `/organizaciones/:org/contexto/` | EXPUESTO | IntelligencePage | GLOBAL | Contexto preparado |
| Contexto | KPIs organización | GET | `/organizaciones/:org/kpis/` | EXPUESTO | environmentalKpiApi | GLOBAL | KPIs preparados |
| Contexto problema | Contexto | GET | `/problemas/:id/contexto/` | EXPUESTO | intelligence | PROBLEMA | IA/usuario entiende caso |
| Contexto problema | Historial | GET | `/problemas/:id/historial/` | EXPUESTO | intelligence | PROBLEMA | Historia sintetizada |
| Contexto problema | Fuentes | GET | `/problemas/:id/fuentes/` | EXPUESTO | intelligence | PROBLEMA | Fuentes relevantes |
| Contexto problema | Acciones previas | GET | `/problemas/:id/acciones-previas/` | EXPUESTO | intelligence | PROBLEMA | Aprender intentos |
| Contexto problema | Evidencias | GET | `/problemas/:id/evidencias-resumen/` | EXPUESTO | intelligence | PROBLEMA | Respaldo sintetizado |
| Contexto problema | Normativa | GET | `/problemas/:id/contexto-normativo/` | EXPUESTO | intelligence | PROBLEMA | Contexto de cumplimiento |
| Contexto problema | Recomendaciones | GET | `/problemas/:id/recomendaciones/` | EXPUESTO | intelligence | PROBLEMA | Recomendaciones contextualizadas |
| Contexto problema | Escalamiento | GET | `/problemas/:id/escalamiento/` | EXPUESTO | intelligence | PROBLEMA | Preparar escalamiento |
| Contexto problema | Expediente | GET | `/problemas/:id/expediente/` | EXPUESTO | intelligence/professional | PROBLEMA | Consolidar caso |
| Materiales | Ciclo de vida | GET | `/materiales/:id/ciclo-vida/` | PARCIAL | intelligence/materiales | DOMINIO | ACV/lineage contextual |

---

# N. MOTOR AMBIENTAL, RECOMENDACIONES Y DECISIÓN

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Motor | Resultados ambientales | GET | `/organizaciones/:org/motor-ambiental/` | EXPUESTO | IntelligencePage | GLOBAL | Detectar señales |
| ACV | Resultados | GET | `/organizaciones/:org/acv/` | PARCIAL | IntelligencePage | GLOBAL | Lectura ciclo de vida |
| KPIs ambientales | Obtener | GET | `/environmental/kpis/:org/` | EXPUESTO | environmentalKpiApi | GLOBAL | Resumen inteligente |
| Recomendaciones | Obtener | GET | `/environmental/recommendations/:org/` | EXPUESTO | IntelligencePage | GLOBAL | Priorizar acciones |
| Escenarios | Obtener | GET | `/environmental/scenarios/:org/` | EXPUESTO | environmentalScenarioApi | GLOBAL | Comparar alternativas calculadas por backend |
| Prioridades | Obtener | GET | `/environmental/decisions/priorities/:org/` | EXPUESTO | IntelligencePage | GLOBAL | Ranking de prioridades |
| Prioridad | Preview de acción | GET | `/environmental/decisions/priorities/:org/:priority/action-preview/` | EXPUESTO | traceableActionsApi | GLOBAL | Revisar antes de crear |
| Prioridad | Crear acción | POST | `/environmental/decisions/priorities/:org/:priority/create-action/` | EXPUESTO | traceableActionsApi | GLOBAL | Convertir recomendación en acción |
| Ejecutivo | Reporte ejecutivo | GET | `/environmental/executive-report/:org/` | EXPUESTO | IntelligencePage | GLOBAL | Resumen ejecutivo |
| Ingesta | Readiness | GET | `/environmental/ingestion-readiness/:org/` | EXPUESTO | IntelligencePage | GLOBAL | Detectar brechas de datos |
| Acción ambiental | Estado cierre | GET | `/environmental/actions/:id/closure-status/` | EXPUESTO | traceableActionsApi | PROBLEMA | Saber si puede cerrarse |
| Acción ambiental | Adjuntar evidencia | POST | `/environmental/actions/:id/attach-evidence/` | EXPUESTO | traceableActionsApi | PROBLEMA | Respaldar ejecución |
| Acción ambiental | Cerrar | POST | `/environmental/actions/:id/close/` | EXPUESTO | traceableActionsApi | PROBLEMA | Cierre verificable |

---

# O. COPILOTO Y CONTEXTO DE AGENTE

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Copiloto | Contexto problema | GET | `/context/problems/:id/` | EXPUESTO | CopilotPage | PROBLEMA | Preparar conversación |
| Copiloto | Contexto activo | GET | `/context/assets/:id/` | EXPUESTO | CopilotPage | GLOBAL | Contexto de activo |
| Copiloto | Mantenimiento activo | GET | `/context/assets/:id/maintenance/` | EXPUESTO | CopilotPage | GLOBAL | Estado mantenimiento |
| Copiloto | Salud sensor | GET | `/context/sensors/:id/health/` | EXPUESTO | CopilotPage | SENSOR | Estado instrumental |
| Copiloto | Historia indicador | GET | `/context/indicators/:id/history/` | EXPUESTO | CopilotPage | OBRA | Serie preparada |
| Copiloto | Evidencia | GET | `/context/evidence/:id/` | EXPUESTO | CopilotPage/dataApi | EVIDENCIA | Documento preparado |
| Copiloto | Memoria organización | GET | `/context/organizations/:org/memory/` | EXPUESTO | CopilotPage | GLOBAL | Contexto persistente |
| Agente | Propuestas | GET/POST | `/agent/problems/:id/proposals/` | EXPUESTO | CopilotPage | PROBLEMA | Consultar/generar propuesta |
| Agente | Feedback | POST | `/agent/problems/:id/proposals/:proposal/feedback/` | EXPUESTO | CopilotPage | PROBLEMA | Aprendizaje por feedback |
| Agente | Borrador reevaluación | POST | `/agent/problems/:id/reevaluation-draft/` | EXPUESTO | CopilotPage | PROBLEMA | Preparar siguiente ciclo sin iniciarlo |
| Agente | Confirmar comando | POST | `/agent/commands/:id/confirm/` | EXPUESTO | CopilotPage | GLOBAL | Human-in-the-loop |

---

# P. CUMPLIMIENTO AMBIENTAL

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Documentos ambientales | Listar | GET | `/organizaciones/:org/documentos-ambientales/` | PARCIAL | gobernanza | GOBERNANZA | Ver documentos regulatorios |
| Documentos ambientales | Crear | POST | `/organizaciones/:org/documentos-ambientales/` | PARCIAL | gobernanza | GOBERNANZA | Registrar documento |
| Documento | Detalle | GET | `/organizaciones/:org/documentos-ambientales/:id/` | PARCIAL | gobernanza | GOBERNANZA | Ver |
| Documento | Editar | PATCH | `/organizaciones/:org/documentos-ambientales/:id/` | PARCIAL | gobernanza | GOBERNANZA | Actualizar |
| Documento | Eliminar | DELETE | `/organizaciones/:org/documentos-ambientales/:id/` | ADMINISTRATIVO | — | GOBERNANZA | Eliminación controlada |
| Variables ambientales | Listar | GET | `/organizaciones/:org/variables-ambientales/` | PARCIAL | gobernanza | GOBERNANZA | Variables extraídas |
| Variables ambientales | Crear | POST | `/organizaciones/:org/variables-ambientales/` | PARCIAL | gobernanza | GOBERNANZA | Registrar variable |
| Variable | Detalle | GET/PATCH/DELETE | `/organizaciones/:org/variables-ambientales/:id/` | PARCIAL | gobernanza | GOBERNANZA | Gestionar variable |
| Límites | Listar | GET | `/organizaciones/:org/limites-ambientales/` | PARCIAL | gobernanza | GOBERNANZA | Límites vigentes |
| Límites | Crear | POST | `/organizaciones/:org/limites-ambientales/` | PARCIAL | gobernanza | GOBERNANZA | Registrar límite validado |
| Límite | Detalle | GET/PATCH/DELETE | `/organizaciones/:org/limites-ambientales/:id/` | PARCIAL | gobernanza | GOBERNANZA | Gestionar límite |
| Alertas | Listar | GET | `/organizaciones/:org/alertas-cumplimiento/` | PARCIAL | GovernanceOverviewPage | GOBERNANZA | Ver alertas |
| Alertas | Actualizar | PATCH | `/organizaciones/:org/alertas-cumplimiento/:id/` | PARCIAL | gobernanza | GOBERNANZA | Revisar/resolver alerta |
| Cumplimiento | Resumen | GET | `/organizaciones/:org/cumplimiento-ambiental/resumen/` | EXPUESTO | GovernanceOverviewPage | GOBERNANZA | Estado agregado |

**Principio:** la UI sólo presenta cumplimiento cuando existe límite/documento validado; de lo contrario muestra “requiere revisión” o “sin base normativa”.

---

# Q. REVISIÓN PROFESIONAL

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Revisión | Listar | GET | `/organizaciones/:org/revisiones-profesionales/` | EXPUESTO | ReviewQueuePage / professionalV2Api | GOBERNANZA | Cola profesional |
| Revisión | Crear | POST | `/organizaciones/:org/revisiones-profesionales/` | EXPUESTO | professionalV2Api | GOBERNANZA | Escalar objeto |
| Revisión | Detalle | GET | `/organizaciones/:org/revisiones-profesionales/:id/` | EXPUESTO | ReviewQueuePage | GOBERNANZA | Ver revisión |
| Revisión | Editar | PATCH | `/organizaciones/:org/revisiones-profesionales/:id/` | EXPUESTO | professionalV2Api | GOBERNANZA | Completar revisión |
| Hallazgo | Crear | POST | `/organizaciones/:org/revisiones-profesionales/:id/hallazgos/` | EXPUESTO | professionalV2Api | GOBERNANZA | Registrar hallazgo |
| Decisión | Emitir | POST | `/organizaciones/:org/revisiones-profesionales/:id/decision/` | EXPUESTO | professionalV2Api | GOBERNANZA | Validar/rechazar/solicitar antecedentes |
| Auditoría | Listar | GET | `/organizaciones/:org/auditoria/` | EXPUESTO | AuditPage | GOBERNANZA | Auditar decisiones |

---

# R. EXPEDIENTES E INFORMES

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Expediente | Listar | GET | `/organizaciones/:org/expedientes/` | EXPUESTO | DossiersPage | GOBERNANZA | Ver expedientes |
| Expediente | Crear | POST | `/organizaciones/:org/expedientes/` | EXPUESTO | professionalV2Api | GOBERNANZA | Consolidar problema |
| Expediente | Detalle | GET | `/organizaciones/:org/expedientes/:id/` | EXPUESTO | DossierDetailPage | GOBERNANZA | Revisar expediente |
| Expediente | Cerrar | POST | `/organizaciones/:org/expedientes/:id/cerrar/` | EXPUESTO | professionalV2Api | GOBERNANZA | Cerrar caso |
| Expediente | Reabrir | POST | `/organizaciones/:org/expedientes/:id/reabrir/` | EXPUESTO | professionalV2Api | GOBERNANZA | Reabrir con motivo |
| Informe | Generar | POST | `/organizaciones/:org/informes/` | EXPUESTO | professionalV2Api | GOBERNANZA | Crear informe versionado |
| Informe | Detalle | GET | `/organizaciones/:org/informes/:id/` | EXPUESTO | DossierDetailPage | GOBERNANZA | Ver informe |
| Informe | PDF | GET | `/organizaciones/:org/informes/:id/pdf/` | EXPUESTO | professionalV2Api | GOBERNANZA | Descargar informe |
| Informe | Validar | POST | `/organizaciones/:org/informes/:id/validar/` | EXPUESTO | professionalV2Api | GOBERNANZA | Validación profesional |

---

# S. CONOCIMIENTO AMBIENTAL

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Conocimiento | Listar casos | GET | `/organizaciones/:org/conocimiento/casos/` | EXPUESTO | KnowledgePage / knowledgeApi | GOBERNANZA | Casos aprendidos |
| Conocimiento | Crear caso desde intervención | POST | `/organizaciones/:org/conocimiento/casos/` | NO_EXPUESTO | knowledgeApi no implementa POST | GOBERNANZA | Convertir resultado validado en caso de conocimiento |
| Conocimiento | Detalle caso | GET | `/organizaciones/:org/conocimiento/casos/:id/` | PARCIAL | backend disponible; knowledgeApi no tiene detalle | GOBERNANZA | Ver contexto/resultado completo |
| Conocimiento | Agregado | GET | `/organizaciones/:org/conocimiento/agregado/` | EXPUESTO | KnowledgePage / knowledgeApi | GOBERNANZA | Aprendizaje agregado |

---

# T. SERVICIOS ORGANIZACIONALES Y ADMINISTRATIVOS ACTUALES

Estos endpoints siguen siendo válidos, pero no deben desplazar el nuevo núcleo operacional.

| Área | Endpoint | Decisión |
|---|---|---|
| Estado organización | `/organizaciones/:org/estado/` | ADMINISTRATIVO; mantener |
| Configuración | `/organizaciones/:org/configuracion/` | ADMINISTRATIVO; mantener |
| Dashboard legacy | `/organizaciones/:org/dashboard/` | No usar como fuente del futuro dashboard de obra |
| Etapas | `/organizaciones/:org/etapas/` | ADMINISTRATIVO/preset |
| Usuarios | `/organizaciones/:org/usuarios/` | ADMINISTRATIVO |
| Reportes legacy | `/organizaciones/:org/reportes/` | Mantener hasta migración a informes V2 |

---

# U. AUTENTICACIÓN, PLATAFORMA Y UTILIDADES

Estos endpoints no son gestión ambiental, pero forman parte del contrato operativo de la aplicación y quedan registrados para que el inventario sea completo.

| Área | Capacidad | Método | Endpoint | Estado UI | Dueño final | Decisión |
|---|---|---|---|---|---|---|
| Auth | Estado de sesión | GET | `/auth/me/` | EXPUESTO | GLOBAL | Mantener |
| Auth | Token CSRF | GET/POST | `/auth/csrf-token/` | EXPUESTO | GLOBAL | Infraestructura |
| Auth | Iniciar sesión | POST | `/auth/login/` | EXPUESTO | GLOBAL | Mantener |
| Auth | Cerrar sesión | POST | `/auth/logout/` | EXPUESTO | GLOBAL | Mantener |
| Auth | Bootstrap inicial | POST | `/auth/bootstrap/` | ADMINISTRATIVO | ADMINISTRACION | Sólo instalación inicial |
| Plataforma | Dashboard legacy global | GET | `/dashboard/` | ADMINISTRATIVO | GLOBAL | No alimentar dashboard final de obra |
| Plataforma | Estado del sistema | GET | `/sistema/estado/` | ADMINISTRATIVO | ADMINISTRACION | Health técnico |
| Utilidad | Calcular distancia geográfica estimada | POST | `/rutas/calcular-distancia/` | ADMINISTRATIVO | DOMINIO | Utilidad; no reemplaza fuente validada/GPS |
| Utilidad | Advisor legacy | POST | `/ai-advisor/` | ADMINISTRATIVO | GLOBAL | No ampliar; sustituido por inteligencia/Copiloto V2 |
| Verificación | Ficha pública de obra | GET | `/verificar/obra/:codigo/` | EXPUESTO | GLOBAL | Mantener como verificación pública |

---

# V. CONTRATOS LEGACY / COMPATIBILIDAD

La existencia de estos endpoints **no significa que deban ampliarse**. La decisión de producto es conservarlos mientras existan flujos o presets dependientes y evitar construir nuevas capacidades encima de ellos.

| Familia legacy | Endpoints | Estado | Decisión |
|---|---|---|---|
| Emisiones legacy | `/organizaciones/:org/registros-emision/`, `/registros-emision/:id/aplicar-factor/`, `/emisiones/` | ADMINISTRATIVO | No usar para nueva captura ambiental V2 |
| Acciones legacy | `/organizaciones/:org/acciones-ambientales/*` | ADMINISTRATIVO | Nuevo workflow principal = Problemáticas/Intervención V2 |
| Forestal legacy | `/organizaciones/:org/lotes-forestales/*` | ADMINISTRATIVO | Mantener preset forestal; no mezclar con construcción |
| Importaciones legacy | `/importaciones/*`, `/organizaciones/:org/importaciones/:kind/*` | ADMINISTRATIVO | Nuevo flujo principal = Ingesta V2 |
| Obras legacy por código | `/obras/*`, `/obras/:codigo/*` | ADMINISTRATIVO | Mantener compatibilidad/verificación pública |
| Factores emisión legacy | `/factores-emision/*`, `/factores/catalogo/` | ADMINISTRATIVO | Nuevo motor = factores ambientales/metodologías V2 |
| Material construcción legacy | `/materiales-construccion/` | ADMINISTRATIVO | Nuevo material = MaterialOperacional V2 |
| Rutas legacy | `/rutas/calcular-distancia/` | ADMINISTRATIVO | Utilidad, no dominio principal |
| AI advisor legacy | `/ai-advisor/` | ADMINISTRATIVO | Nuevo Copiloto/Inteligencia V2 |
| Intelligence legacy | `/intelligence/context/`, `/intelligence/recommendations/` | ADMINISTRATIVO | Mantener sólo si páginas aún dependen |
| Dashboard global legacy | `/dashboard/` | ADMINISTRATIVO | No usar como dashboard final de obra |
| Sistema | `/sistema/estado/` | ADMINISTRATIVO | Health/diagnóstico técnico |

---

# W. IOT LEGACY / INGESTA DE DISPOSITIVOS

Backend adicional `backend/apps/iot/urls.py`.

| Capacidad | Método/uso | Endpoint | Estado | Decisión |
|---|---|---|---|---|
| Lecturas legacy | POST | `/iot/lecturas/` | ADMINISTRATIVO | No confundir con LecturaSensorV2 |
| KPIs legacy | GET | `/iot/kpis/` | ADMINISTRATIVO | Compatibilidad |
| Últimas lecturas | GET | `/iot/lecturas/ultimas/` | ADMINISTRATIVO | Compatibilidad |
| Dispositivos ingestión | GET/POST | `/iot/dispositivos/` | ADMINISTRATIVO | Gateway de dispositivo |
| Detalle dispositivo | GET/PATCH | `/iot/dispositivos/:id/` | ADMINISTRATIVO | Gateway |
| Ingesta IoT | POST | `/iot/ingesta/` | ADMINISTRATIVO | Entrada máquina-a-máquina |
| Registros sensor | GET | `/iot/registros/` | ADMINISTRATIVO | Diagnóstico |
| KPIs operacionales IoT | GET | `/iot/operacion/kpis/` | ADMINISTRATIVO | Diagnóstico |

**Contrato final IoT:** dispositivo/raw → `LecturaSensorV2` → `Observacion` → actividad/dominio. Ningún endpoint legacy tiene autoridad para inventar impacto ambiental.

---

# X. RUTAS FRONTEND ACTUALES Y DUEÑO FINAL

| Ruta frontend | Rol final |
|---|---|
| `/inicio` | Portada global |
| `/obras` | Selector de universo operacional |
| `/obras/:obraId/resumen` | Futuro Centro de Mando Ambiental de la Obra |
| `/obras/:obraId/operacion` | Resumen operacional |
| `/obras/:obraId/operacion/energia` | Dominio Energía |
| `/obras/:obraId/operacion/agua` | Dominio Agua |
| `/obras/:obraId/operacion/combustibles` | Dominio Combustibles |
| `/obras/:obraId/operacion/transporte` | Dominio Transporte |
| `/obras/:obraId/operacion/materiales` | Dominio Materiales |
| `/obras/:obraId/operacion/residuos` | Dominio Residuos |
| `/obras/:obraId/operacion/ruido` | Dominio Ruido |
| `/obras/:obraId/operacion/hidrica-suelo` | Dominio Hídrica y suelo |
| `/obras/:obraId/indicadores` | Indicadores de obra |
| `/obras/:obraId/problemas` | Gestión ambiental de la obra |
| `/obras/:obraId/evidencias` | Evidencia de la obra |
| `/obras/:obraId/timeline` | Historial de la obra |
| `/datos/evidencias` | Biblioteca global de evidencia |
| `/datos/importaciones` | Ingesta/importación |
| `/operacion/activos` | Administración global de activos |
| `/operacion/sensores` | Administración global de sensores |
| `/inteligencia` | Inteligencia ambiental |
| `/inteligencia/copiloto` | Copiloto |
| `/gobernanza/*` | Calidad, revisión profesional, expedientes, factores, auditoría, conocimiento |
| `/administracion/*` | Organización, usuarios, configuración y estructura |

---

# Y. DUPLICIDADES DE SERVICIOS FRONTEND — DECISIÓN

## Se conservan como agregadores
- `frontend/src/features/operacion/services/operationApi.js`
  - Sólo agregación de lectura para workspace de obra.
  - No agregar nuevos writes aquí.

## Clientes API dueños
- Diagnóstico: `features/diagnostico/api/diagnosticoApi.js`
- Evidencia/ingesta: `features/datos/services/dataApi.js`
- Activos: `features/activos/api/assetsApi.js`
- Sensores: `features/sensores/api/sensorsApi.js`
- Flujos: `features/operacion/api/sectorFlowsApi.js`
- Transporte: `features/operacion/api/transportApi.js`
- Materiales: `features/operacion/api/materialsApi.js`
- Cálculo: `features/operacion/api/calculationV2Api.js`
- Problemas: `features/mejora/services/improvementApi.js`
- Profesional: `features/professional/api/professionalV2Api.js`
- Inteligencia: servicios de `features/environmental` y `features/intelligence`
- Conocimiento: `features/knowledge/api/knowledgeApi.js`

**Regla:** ninguna page debe volver a construir URLs de negocio inline si existe un cliente API dueño.

---

# Z. MATRIZ TRANSVERSAL DE ERRORES

| Situación | HTTP esperado | UX final |
|---|---:|---|
| No autenticado | 401/403 | Sesión expirada / acceso requerido |
| Permiso insuficiente | 403 | Explicar capacidad requerida |
| Recurso de otro tenant | 404 | Recurso no disponible |
| Recurso de otra obra | 404 | Recurso no disponible |
| Payload inválido | 400 | Mostrar error junto al campo |
| Estado incompatible | 400 | Explicar qué falta antes de continuar |
| Recurso duplicado/conflicto | 409 | Explicar conflicto y conservar formulario |
| Recurso inexistente | 404 | Estado de recurso no encontrado |
| Error inesperado | 5xx | Error recuperable + reintentar |

---

# AA. MATRIZ DE PERMISOS DE PRODUCTO

| Capacidad | Usuario organización | Admin organización | Profesional | Superusuario |
|---|---|---|---|---|
| Consultar operación | Sí según pertenencia | Sí | Sí según pertenencia | Sí |
| Capturar datos | Sí según rol | Sí | Sí según rol | Sí |
| Configurar estructura | Limitado | Sí | Según rol | Sí |
| Gestionar metodología organizacional | No por defecto | Sí | Sí si autorizado | Sí |
| Modificar metodología global | No | No | No | Sí |
| Emitir decisión profesional | No | Sólo si tiene capacidad profesional | Sí | Sí |
| Cerrar expediente/informe | Según workflow | Sí según workflow | Sí | Sí |
| Acceder a otro tenant | No | No | No | Sólo por privilegio explícito |

---

# AB. BRECHAS FUNCIONALES QUE PASAN AL PASO 2+ DEL PLAN MAESTRO

Estas brechas **no son omisiones del contrato**; están inventariadas y se convierten en trabajo explícito del roadmap.

## P0 — Fundación de obra
1. Diagnóstico/aplicabilidad dentro de `/obras/:obraId`.
2. Edición de estructura operacional donde corresponda.
3. Puntos ambientales creados desde dominios.
4. Eliminar callejones muertos de “Por definir”.

## P0 — Captura
5. Crear/editar flujos ambientales desde Energía, Agua, Combustibles, Residuos, Ruido e Hídrica/Suelo.
6. Crear fuente durante captura cuando no exista.
7. Navegar Registro → Observación → Fuente → Evidencia.
8. Mostrar importación confirmada dentro del dominio de destino.

## P0 — Transporte
9. CRUD funcional de rutas/viajes.
10. Detalle auditable de viaje.

## P0 — Materiales
11. CRUD de material/lote/evento.
12. Balance.
13. Lineage.

## P0 — Problemas
14. Completar UI para alcance e indicadores.
15. Workspace de resolución sin huecos.

## P1
16. Sensores contextualizados en dominios.
17. Calidad visible junto al dato.
18. Cálculo/impacto navegable desde actividad.
19. Series, líneas base y comparaciones completas.
20. Cumplimiento conectado a dominio/problema.
21. Inteligencia convertida en acciones trazables.

## P2
22. Revisión profesional y expediente completamente integrados al caso.
23. Centro de Mando Ambiental de la Obra.
24. Prueba E2E obra vacía → informe.

---

# AC. GATE DE CIERRE DE ESTA FASE

La Fase 1 sólo se considera cerrada cuando:

- [x] Todas las familias de endpoints de negocio actuales tienen una decisión de producto.
- [x] El backend V2 y los contratos legacy están separados explícitamente.
- [x] Se identificó el dueño visual final de cada capacidad.
- [x] Se definieron clientes API dueños por feature.
- [x] Se definió el contrato transversal de errores.
- [x] Se definió el criterio de permisos.
- [x] Las capacidades no expuestas quedaron registradas como brechas del roadmap.
- [ ] El archivo fue incorporado al repositorio y validado contra el commit final.
- [ ] `npm run lint`, `npm run build` y `git diff --check` pasan tras el reemplazo.

**Resultado esperado del Paso 1:** Carbono Zero deja de desarrollar “pantallas sueltas”. Desde este punto, cualquier trabajo funcional debe poder rastrearse a una capacidad de este contrato y a una etapa del Plan Maestro de Cierre.
