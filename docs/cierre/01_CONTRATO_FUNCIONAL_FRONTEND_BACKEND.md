# Carbono Zero — Contrato funcional Frontend ↔ Backend

Base auditada:
- rama: main
- commit: 1b4658d1285d1701691c77fb6fc278adf29a050a

## Estados

- EXPUESTO: frontend permite ejecutar correctamente la capacidad.
- PARCIAL: frontend usa parte del contrato, pero faltan operaciones o contexto.
- NO_EXPUESTO: backend lo soporta, frontend no ofrece flujo.
- ADMINISTRATIVO: capacidad intencionalmente fuera del flujo operacional principal.
- REVISAR: existe integración frontend, pero falta verificar cobertura completa.

## Dueños visuales

- GLOBAL
- OBRA
- DOMINIO
- PROBLEMA
- EVIDENCIA
- SENSOR
- GOBERNANZA
- ADMINISTRACION

## Matriz

| Área | Capacidad backend | Método | Endpoint | Estado UI | Frontend actual | Dueño final | Flujo final |
|---|---|---|---|---|---|---|---|
| Diagnóstico | Obtener diagnóstico | GET | /organizaciones/:org/diagnostico-ambiental/?obra=:obra | PARCIAL | diagnosticoApi.js | OBRA | Consultar diagnóstico de la obra |
| Diagnóstico | Crear diagnóstico | POST | /organizaciones/:org/diagnostico-ambiental/ | PARCIAL | diagnosticoApi.js | OBRA | Completar diagnóstico desde obra |
| Diagnóstico | Editar diagnóstico | PATCH | /organizaciones/:org/diagnostico-ambiental/ | PARCIAL | diagnosticoApi.js | OBRA | Actualizar diagnóstico de la obra |
| Puntos ambientales | Listar puntos | GET | /organizaciones/:org/puntos-ambientales/?obra=:obra | EXPUESTO_LECTURA | operationApi.js | DOMINIO | Ver puntos del dominio |
| Puntos ambientales | Crear punto | POST | /organizaciones/:org/puntos-ambientales/ | NO_EXPUESTO | — | DOMINIO | Crear punto desde Energía/Agua/Ruido/etc. |
| Flujos ambientales | Listar registros | GET | /organizaciones/:org/flujos-ambientales/?obra=:obra | EXPUESTO_LECTURA | operationApi.js | DOMINIO | Ver registros |
| Flujos ambientales | Registrar dato | POST | /organizaciones/:org/flujos-ambientales/ | NO_EXPUESTO | — | DOMINIO | Registrar lectura/consumo/condición |
| Flujos ambientales | Editar registro | PATCH | /organizaciones/:org/flujos-ambientales/:id/ | NO_EXPUESTO | — | DOMINIO | Corregir registro |
| Transporte | Listar rutas | GET | /organizaciones/:org/rutas-operacionales/ | NO_EXPUESTO | — | DOMINIO | Administrar rutas |
| Transporte | Crear ruta | POST | /organizaciones/:org/rutas-operacionales/ | NO_EXPUESTO | — | DOMINIO | Crear ruta |
| Transporte | Listar viajes | GET | /organizaciones/:org/viajes-operacionales/?obra=:obra | EXPUESTO_LECTURA | operationApi.js | DOMINIO | Ver viajes |
| Transporte | Registrar viaje | POST | /organizaciones/:org/viajes-operacionales/ | NO_EXPUESTO | — | DOMINIO | Registrar viaje |
| Transporte | Editar viaje | PATCH | /organizaciones/:org/viajes-operacionales/:id/ | NO_EXPUESTO | — | DOMINIO | Editar viaje |
| Transporte | Indicadores | GET | /organizaciones/:org/viajes-operacionales/indicadores/?obra=:obra | EXPUESTO | operationApi.js | DOMINIO | Estado de transporte |
| Materiales | Listar materiales | GET | /organizaciones/:org/materiales-operacionales/ | NO_EXPUESTO_DIRECTO | — | DOMINIO | Catálogo operacional |
| Materiales | Crear material | POST | /organizaciones/:org/materiales-operacionales/ | NO_EXPUESTO | — | DOMINIO | Registrar material |
| Materiales | Editar material | PATCH | /organizaciones/:org/materiales-operacionales/:id/ | NO_EXPUESTO | — | DOMINIO | Editar material |
| Materiales | Listar lotes | GET | /organizaciones/:org/lotes-materiales/ | NO_EXPUESTO | — | DOMINIO | Ver lotes |
| Materiales | Crear lote | POST | /organizaciones/:org/lotes-materiales/ | NO_EXPUESTO | — | DOMINIO | Crear lote |
| Materiales | Listar movimientos | GET | /organizaciones/:org/eventos-materiales/?obra=:obra | EXPUESTO_LECTURA | operationApi.js | DOMINIO | Ver movimientos |
| Materiales | Crear movimiento | POST | /organizaciones/:org/eventos-materiales/ | NO_EXPUESTO | — | DOMINIO | Registrar entrada/uso/salida/residuo |
| Materiales | Editar movimiento | PATCH | /organizaciones/:org/eventos-materiales/:id/ | NO_EXPUESTO | — | DOMINIO | Editar movimiento |
| Materiales | Balance | GET | /organizaciones/:org/materiales-operacionales/:id/balance/ | NO_EXPUESTO | — | DOMINIO | Ver balance |
| Materiales | Lineage | GET | /organizaciones/:org/materiales-operacionales/:id/lineage/ | NO_EXPUESTO | — | DOMINIO | Reconstruir trazabilidad |
| Problemas | Listar/crear problema | GET/POST | /organizaciones/:org/problematicas/ | EXPUESTO | improvementApi.js | PROBLEMA | Gestión de problemas |
| Problemas | Acciones | GET/POST | .../problematicas/:id/acciones/ | EXPUESTO | improvementApi.js | PROBLEMA | Proponer acciones |
| Problemas | Seleccionar acción | POST | .../seleccionar/ | EXPUESTO | improvementApi.js | PROBLEMA | Seleccionar acción |
| Problemas | Iniciar acción | POST | .../iniciar/ | EXPUESTO | improvementApi.js | PROBLEMA | Iniciar ejecución |
| Problemas | Implementar acción | POST | .../implementar/ | EXPUESTO | improvementApi.js | PROBLEMA | Implementar |
| Problemas | Seguimiento | GET/POST | .../seguimientos/ | EXPUESTO | improvementApi.js | PROBLEMA | Medir seguimiento |
| Problemas | Medir desde motor | POST | .../seguimientos/motor/ | EXPUESTO | improvementApi.js | PROBLEMA | Obtener medición gobernada |
| Problemas | Evaluar | POST | .../evaluar/ | EXPUESTO | improvementApi.js | PROBLEMA | Evaluar resultado |
| Problemas | Reevaluar | POST | .../reevaluar/ | EXPUESTO | improvementApi.js | PROBLEMA | Nuevo ciclo |
| Problemas | Escalar | POST | .../escalar/ | EXPUESTO | improvementApi.js | PROBLEMA | Escalar a profesional |
| Problemas | Historial | GET | .../historial/ | EXPUESTO | improvementApi.js | PROBLEMA | Ver trazabilidad |
## Contrato transversal de errores

| Situación | HTTP esperado | UX final |
|---|---:|---|
| No autenticado | 401/403 | Sesión expirada / acceso requerido |
| Recurso de otro tenant | 404 | Recurso no disponible |
| Recurso de otra obra | 404 | Recurso no disponible |
| Payload inválido | 400 | Mostrar errores junto al campo correspondiente |
| Estado incompatible | 400 | Explicar qué falta antes de continuar |
| Recurso duplicado/conflicto | 409 | Explicar conflicto y conservar formulario |
| Recurso inexistente | 404 | Mostrar estado de recurso no encontrado |
| Error inesperado | 5xx | Mostrar error recuperable y permitir reintentar |