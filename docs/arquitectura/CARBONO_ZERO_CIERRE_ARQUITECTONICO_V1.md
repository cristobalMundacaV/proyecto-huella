# Carbono Zero V1 — cierre arquitectónico

Auditoría realizada sobre `5ff2765` y el estado de trabajo de Fase 17. La clasificación expresa capacidad V1; no convierte decisiones ambientales externas en software ni en factores científicos.

## Matriz RF-001–RF-100

| RF | Estado | Implementación | Evidencia código/test | Limitación |
|---|---|---|---|---|
| RF-001 | CUMPLIDO | Organización tenant y membresías | `Organizacion`, `UsuarioOrganizacion`; `test_foundation.py` | — |
| RF-002 | CUMPLIDO | Diagnóstico general y por obra | `DiagnosticoAmbientalInicial`; `test_construction_v1.py` | — |
| RF-003 | CUMPLIDO | Elementos de diagnóstico con identidad | `DiagnosticoAmbientalSerializer`; `test_foundation.py` | — |
| RF-004 | CUMPLIDO | Capacidades configurables | `CapacidadOrganizacion`, `AplicabilidadCapacidadObra` | — |
| RF-005 | CUMPLIDO | Preset identificado por organización | `Organizacion.preset`, `foundation.py` | — |
| RF-006 | CUMPLIDO | Unidades, procesos, activos y obras | modelos Activity Core; `test_activity_core.py` | — |
| RF-007 | CUMPLIDO_CON_LIMITACION | Comparabilidad explícita temporal | `PeriodoComparable`, `comparison_v2.py` | No presume comparabilidad científica entre obras. |
| RF-008 | CUMPLIDO | Presets iniciales extensibles | `Organizacion.Preset`, configuración frontend | — |
| RF-009 | CUMPLIDO | Capacidad activa/inactiva preserva identidad | `CapacidadOrganizacion.estado` | — |
| RF-010 | CUMPLIDO | Estructura operacional flexible | `UnidadOperacional`, `ProcesoOperacional`, `ActivoOperacional` | — |
| RF-011 | CUMPLIDO | Ingesta tabular | `ProcesoIngesta`, `ingestion_v2.py` | — |
| RF-012 | CUMPLIDO_CON_LIMITACION | Ingesta documental versionada | `EvidenciaObra`, `VersionEvidencia` | Extracción depende del formato soportado; no hay OCR general. |
| RF-013 | CUMPLIDO | Entrada manual estructurada | `crear_ingesta_estructurada` | — |
| RF-014 | CUMPLIDO | Entrada API por core común | `crear_ingesta_estructurada`; `test_ingestion_multisource_v1.py` | No incluye conectores ERP externos. |
| RF-015 | CUMPLIDO | Sensor y telemetría sin documento ficticio | `ProcesoIngesta.version_evidencia` nullable | — |
| RF-016 | CUMPLIDO | Clasificación sugerida y confirmada | campos de `ProcesoIngesta` | — |
| RF-017 | CUMPLIDO | Contexto sugerido/confirmado tenant-safe | `_context_suggestions`, `contexto_confirmado` | — |
| RF-018 | CUMPLIDO | Raw y normalizado separados | `RegistroExtraido.datos_originales/datos_normalizados` | — |
| RF-019 | CUMPLIDO | Plantillas versionadas por tenant | `PlantillaMapeo`, `MapeoColumna` | — |
| RF-020 | CUMPLIDO | Preview, revisión e idempotencia | `preview_ingesta`, `confirmar_ingesta` | — |
| RF-021 | CUMPLIDO | Provenance extremo a extremo | `Observacion`, `RegistroExtraido`, `VersionEvidencia` | — |
| RF-022 | CUMPLIDO | Método y naturaleza por canal | `PROVENANCE_BY_INGESTION` | Enums usan equivalentes existentes para sensor/telemetría. |
| RF-023 | CUMPLIDO | Fuente separada de calidad del dato | `FuenteDatos`, `EvaluacionCalidadDato` | — |
| RF-024 | CUMPLIDO | Estados de calidad globales | `EvaluacionCalidadDato.Estado` | — |
| RF-025 | CUMPLIDO | Criticidad metodológica de variables | `VariableFormula.criticidad` | — |
| RF-026 | CUMPLIDO | Campo crítico faltante bloquea cálculo | selector/cálculo V2; `test_calculation_v2.py` | — |
| RF-027 | CUMPLIDO | No existe estimación silenciosa | normalización y motor metodológico | — |
| RF-028 | CUMPLIDO | Imposibles e inconsistencias se señalan | quality resolver y handlers | — |
| RF-029 | CUMPLIDO_CON_LIMITACION | Política de confianza tenant/global | `PoliticaConfianzaFuente`, `ObservationResolver` | Prioridad configurada por concepto/tipo de fuente. |
| RF-030 | CUMPLIDO_CON_LIMITACION | Selección confiable sólo bajo política | `ObservationResolver` | Ante duda conserva revisión humana. |
| RF-031 | CUMPLIDO | Actividad como evento central | `ActividadOperacional` | — |
| RF-032 | CUMPLIDO | Observaciones complementarias por actividad | FK observación–actividad | — |
| RF-033 | CUMPLIDO_CON_LIMITACION | Duplicado técnico conservador | `is_technical_duplicate` | No hace deduplicación semántica general. |
| RF-034 | CUMPLIDO | Métodos alternativos no se suman | selector metodológico; `test_methodology_v2.py` | — |
| RF-035 | CUMPLIDO | Navegación bidireccional | related names y serializers de detalle | — |
| RF-036 | CUMPLIDO | Identidad y estado de activos | `ActivoOperacional`, condiciones | — |
| RF-037 | CUMPLIDO | Mantenimiento de activos | `MantenimientoActivo` | — |
| RF-038 | CUMPLIDO | Maquinaria y horas/ralentí observables | `Maquinaria`, observaciones | Conversión ambiental depende de metodología. |
| RF-039 | CUMPLIDO | Instalación y prueba de sensores | `InstalacionSensor`, `LecturaSensorV2` | — |
| RF-040 | CUMPLIDO | Calibración y mantenimiento sensor | `CalibracionSensor` | — |
| RF-041 | CUMPLIDO | Estado/calidad instrumental heredada | services sensor V2; tests IoT | — |
| RF-042 | CUMPLIDO | Lifecycle metodológico gobernado | `VersionMetodologia.Estado` | — |
| RF-043 | CUMPLIDO | Revisión profesional metodológica | `RevisionProfesionalAmbiental.version_metodologia` | — |
| RF-044 | CUMPLIDO | Fórmula segura sin `eval`/`exec` | parser de fórmulas; búsqueda estática F17 | — |
| RF-045 | CUMPLIDO | Variables y criticidad | `VariableFormula` | — |
| RF-046 | CUMPLIDO | Aplicabilidad y prioridad | `VersionMetodologia.aplicabilidad/prioridad` | — |
| RF-047 | CUMPLIDO | Selector determinístico | calculation/methodology services | — |
| RF-048 | CUMPLIDO | Factores globales/tenant y vigencia | `FactorAmbiental`, `VersionFactorAmbiental` | — |
| RF-049 | CUMPLIDO | Snapshot técnico e inputs | `CalculoAmbiental`, `InputCalculoAmbiental` | — |
| RF-050 | CUMPLIDO | Recálculo crea nueva historia | `recalculo_de`, comparison service | — |
| RF-051 | CUMPLIDO | Viaje operacional central | `ViajeOperacional` | — |
| RF-052 | CUMPLIDO | Vehículo, ruta, tiempos y estados | `Vehiculo`, `RutaOperacional`, viaje | — |
| RF-053 | CUMPLIDO | Distancia, carga, t·km y combustible | `journey_metrics` | Sólo unidades compatibles. |
| RF-054 | CUMPLIDO | Vacío y retorno diferenciados | `estado_carga`, `tipo_trayecto` | — |
| RF-055 | CUMPLIDO | Utilización y consolidación informativa | `transport_indicators` | No optimiza rutas automáticamente. |
| RF-056 | CUMPLIDO | Sólo viajes completados en indicadores | `transport_indicators` | — |
| RF-057 | PENDIENTE_VALIDACION_EXTERNA | Tercerizado representable y trazable | `tipo_gestion`, `metodologia_tercerizado` | Metodología definitiva pendiente. |
| RF-058 | CUMPLIDO | Material, lote y eventos diferenciados | `MaterialOperacional`, `LoteMaterial`, `EventoMaterial` | — |
| RF-059 | CUMPLIDO | Compra no equivale a uso; lineage | `materials_v2.py`; `test_materials_v2.py` | — |
| RF-060 | CUMPLIDO_CON_LIMITACION | Balance temporal por unidad/obra | `material_balance` | Impacto incorporado requiere EPD/LCA validado. |
| RF-061 | CUMPLIDO | Energía con granularidad explícita | `RegistroFlujoAmbiental` | No reparte facturas automáticamente. |
| RF-062 | CUMPLIDO | Generación separada del consumo | flujo `generacion_propia` | No se trata automáticamente como reducción. |
| RF-063 | PENDIENTE_VALIDACION_EXTERNA | Agua capturable y trazable | flujo `agua` | Regla sin medición/documento pendiente. |
| RF-064 | CUMPLIDO_CON_LIMITACION | Residuos y destinos diferenciados | flujo `residuo`, `DestinoResiduo` | Equivalencias ambientales requieren validación. |
| RF-065 | CUMPLIDO | Flujos sectoriales no reducidos a CO2e | `sector_summary` | Cálculo sólo cuando existe metodología. |
| RF-066 | CUMPLIDO | Indicadores absolutos | `IndicadorAmbiental.Tipo.ABSOLUTO` | — |
| RF-067 | CUMPLIDO | Indicadores de intensidad | `Tipo.INTENSIDAD` | Denominador requerido. |
| RF-068 | CUMPLIDO | Indicadores operacionales/problemáticos | tipos `OPERACIONAL/PROBLEMATICA` | — |
| RF-069 | CUMPLIDO | Alcance flexible de problemática | `AlcanceProblematica` | — |
| RF-070 | CUMPLIDO | Componentes específicos dentro de obra | scope unidad/proceso/activo/actividad | — |
| RF-071 | CUMPLIDO | KPIs vinculados al problema | `IndicadorProblematica` | — |
| RF-072 | CUMPLIDO | BASE congelada | `SnapshotIntervencion`, `SnapshotValorIndicador` | — |
| RF-073 | CUMPLIDO | RESULT con mismo scope/KPI | `intervention_v2.py` | — |
| RF-074 | CUMPLIDO | Estados de resultado explícitos | `ResultadoIntervencion.Estado` | No presume causalidad. |
| RF-075 | CUMPLIDO | Máximo tres ciclos antes de escalar | `select_action`, `escalate_problem`; tests intervención | — |
| RF-076 | CUMPLIDO | Cambio de meta justificado/versionado | `HistorialMetaProblematica`, `change_target` | — |
| RF-077 | CUMPLIDO | Implementación separada de efecto | acción, ciclo y resultado separados | — |
| RF-078 | CUMPLIDO | Ley de mínimo contexto | `ContextGateway` | Límites por paquete. |
| RF-079 | CUMPLIDO_CON_LIMITACION | Contextos especializados | problem/asset/sensor/indicator/evidence/activity/work | Rutas/viajes/materiales se incluyen por activity/work, no todos tienen endpoint aislado. |
| RF-080 | CUMPLIDO | IA no recibe ORM/querysets | paquetes JSON-safe y tests Copiloto | — |
| RF-081 | CUMPLIDO | Contexto procesado antes de IA | `ContextGateway` | — |
| RF-082 | CUMPLIDO_CON_LIMITACION | Feedback/restricción iterativa | proposals/feedback/commands | No es agente autónomo general. |
| RF-083 | CUMPLIDO | Recomendaciones estructuradas | `RecomendacionAgenteAmbiental` | — |
| RF-084 | CUMPLIDO | Memoria resumida persistente | `MemoriaOrganizacion` | — |
| RF-085 | CUMPLIDO | Restricciones vigentes/temporales | `RestriccionContextual` | — |
| RF-086 | CUMPLIDO | IA propone, humano formaliza | comandos e intervención | — |
| RF-087 | CUMPLIDO | Hitos IA auditados | `HitoDecisionIA` | — |
| RF-088 | CUMPLIDO | Casos de conocimiento versionados | `CasoConocimientoAmbiental` | — |
| RF-089 | CUMPLIDO | Resultados éxito/fracaso/no viable | knowledge service | — |
| RF-090 | CUMPLIDO | Provenance de conocimiento verificada | origen backend; tests knowledge | — |
| RF-091 | CUMPLIDO | Aislamiento y anonimización | `aggregate_knowledge` | — |
| RF-092 | CUMPLIDO | Conocimiento no altera ciencia | separación de metodologías/factores | — |
| RF-093 | CUMPLIDO_CON_LIMITACION | Reporte técnico con trazabilidad | professional/report services | Presentación visual PDF continúa evolutiva. |
| RF-094 | CUMPLIDO | Dossier de problemática | `ExpedienteAmbiental`, dossier services | — |
| RF-095 | CUMPLIDO | Decisiones profesionales tipadas | `RevisionProfesionalAmbiental` | — |
| RF-096 | CUMPLIDO | Profesional, fecha, comentario y versión | revisión/informe/snapshot | — |
| RF-097 | CUMPLIDO | Escalamiento y retorno al ciclo | professional/intervention services | — |
| RF-098 | CUMPLIDO | Corrección crea nueva historia | `CorreccionHistoricaAmbiental` | — |
| RF-099 | CUMPLIDO | Historia auditable | eventos, snapshots, revisiones, versiones | — |
| RF-100 | CUMPLIDO | Automático normal; humano en excepción | ingesta, resolver, cálculo, profesional | — |

## H1–H6 Construcción

| Hallazgo | Estado | Evidencia |
|---|---|---|
| H1 Obra como frontera | CUMPLIDO | `ActividadOperacional.obra`, scopes de flujos/materiales/problemas; `test_construction_v1.py` |
| H2 Indicadores por obra | CUMPLIDO | constraints condicionados y filtrado `actividad__obra` |
| H3 Perfiles dentro de un preset | CUMPLIDO | `Obra.perfil_ambiental` |
| H4 Ruido | CUMPLIDO_CON_LIMITACION | punto/actividad/observación/flujo/problema; sin cumplimiento acústico inventado |
| H5 Hídrica/suelo | CUMPLIDO_CON_LIMITACION | señales y flujo sectorial; sin escorrentía ficticia |
| H6 Inicio a cierre | CUMPLIDO | `environmental_timeline`, cierre real vs pendiente |

## Requerimientos no funcionales

| RNF | Estado | Evidencia / decisión |
|---|---|---|
| Multi-tenant | CUMPLIDO | permisos DRF por defecto, filtros tenant, `test_architecture_closure_v1.py` y suites transversales |
| Auditoría old/new | CUMPLIDO_CON_LIMITACION | cambios sensibles versionados; CRUD trivial no genera auditoría general |
| Inmutabilidad | CUMPLIDO | versiones, cálculos, raw confirmado, snapshots y PDF validado protegidos |
| Explicabilidad | CUMPLIDO | inputs, observaciones, fórmula, factor, versiones y fuentes navegables |
| Seguridad IA | CUMPLIDO | IA consume gateways y no calcula/modifica ciencia |
| Mínimo contexto | CUMPLIDO | paquetes compactos con límites explícitos |
| Extensibilidad | CUMPLIDO | registros de handlers, choices y servicios por flujo dentro del monolito modular |
| Estados del dato | CUMPLIDO | completo/incompleto/no calculable/revisión/inconsistente diferenciados |
| Originales preservados | CUMPLIDO | archivo, checksum, versión, raw y normalizado separados |
| Reportes | CUMPLIDO_CON_LIMITACION | scope y versiones incluidos; diseño visual no es criterio científico |
| Privacidad de conocimiento | CUMPLIDO | agregados anonimizados sin evidencia privada |
| Vigencia metodológica | CUMPLIDO | lifecycle y versiones inmutables |

## Defectos reales corregidos en Fase 17

1. PostgreSQL no podía aplicar `analytics.0012`: se reparó condicionalmente el rename histórico `constructora_id → organizacion_id` antes de alterar FKs.
2. La API no exigía autenticación por defecto: se estableció `IsAuthenticated`, dejando explícitamente públicas sólo autenticación, estado y verificación de obra.
3. Endpoints legacy de obra y dashboard podían consultar otros tenants: ahora filtran por membresías activas o superusuario.
4. Lint frontend usaba `EmissionValue` y `RiskMessage` sin definición: se restauraron import/componente.
5. IoT legacy dependía de acceso anónimo y aceptaba dispositivos sin clave: lecturas humanas requieren membresía tenant y la ingesta máquina-a-máquina exige una API key configurada por dispositivo.

## Pendientes de validación ambiental / regulatoria

1. Metodología formal para transporte tercerizado.
2. Condiciones exactas y prioridad técnica entre metodologías de transporte.
3. Tratamiento de agua sin documento o medición formal.
4. Uso de horas de maquinaria como sustituto de combustible.
5. EPD, LCA y factores de materiales.
6. Equivalencias de reciclaje, valorización y disposición.
7. Condiciones y disclosure de datos estimados.
8. Límites y metodología acústica.
9. Cálculo de escorrentía e infiltración.
10. Normativa sectorial específica por jurisdicción.

## Deuda técnica no bloqueante

- `models.py` y algunas vistas legacy son archivos grandes.
- ESLint mantiene avisos de dependencias de hooks sin errores.
- Bundle frontend principal supera 500 kB y requiere futura separación de chunks.
- Conviven nombres legacy (`RegistroEmision`, `TransporteObra`, `MaterialConstruccion`) por compatibilidad; no son autoridad del core nuevo.
- Algunos contextos especializados se exponen como secciones de paquetes mayores en vez de endpoints individuales.

## Evidencia de cierre

- PostgreSQL del proyecto: PostgreSQL 16, `127.0.0.1:5433`, migraciones analytics 0001–0042 e IoT 0001–0005 aplicadas.
- Regresión final `apps.analytics`: 281 pruebas aprobadas después de los fixes de seguridad.
- IoT final: 6 pruebas aprobadas; 3 pruebas transversales adicionales de cierre/tenant aprobadas.
- Frontend: build aprobado; lint sin errores después del correctivo, con 19 warnings.
- Búsqueda estática: no se encontraron llamadas Python a `eval()` o `exec()` en backend productivo.
