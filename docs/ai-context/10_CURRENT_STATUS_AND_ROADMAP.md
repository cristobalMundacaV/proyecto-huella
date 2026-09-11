# Carbono Zero — Estado actual y roadmap

## Corte

**Fecha:** 2026-09-11

## Estado técnico

Carbono Zero ha evolucionado desde un sistema de construcción basado en registros de emisión hacia una arquitectura formal con Operational Kernel, captura unificada y motor ambiental genérico.

Documentación ARQ reciente confirma cierres de Operational Kernel, Unified Capture y Generic Environmental Engine.

## Estado de producto

El proyecto está avanzado, pero no debe declararse terminado. Contexto reciente del fundador: desarrollo intensivo durante agosto/septiembre, presets y arquitectura ambiental trabajados, validación con especialista ambiental y objetivo de cierre durante septiembre.

## Lo validado

- datos ambientales dispersos son problema real;
- trazabilidad es central;
- múltiples fuentes deben convivir;
- calidad/procedencia importan;
- núcleo + presets sectoriales tiene sentido;
- validación humana sigue siendo importante.

## Pendiente de validar/cerrar

No asumir resuelto sin evidencia actual: reglas exactas de prioridad entre fuentes, deduplicación completa, transporte tercerizado, ciclo de vida, madurez transporte/industrial, todas las integraciones oficiales planificadas y cierre productivo completo.

## Prioridades

### P0 — Integridad arquitectónica
Mantener separación Kernel / Environment / Calculation; evitar nuevas dependencias legacy; preservar tenant/workspace/evidence.

### P0 — Flujos reales
Convertir validación experta en reglas implementables de fuentes, campos, evidencias, validación, deduplicación y calidad.

### P1 — Presets
Completar solo rubros con flujo validado.

### P1 — Fuentes oficiales
Implementar integraciones una por una con gobernanza y versionado.

### P1 — Reporting
Todo resultado debe trazarse hasta entrada/evidencia.

### P2 — IA/IoT
Profundizar solo donde exista valor medible.

## Criterio de madurez

Carbono Zero está listo para una organización real cuando captura información sin forzar procesos artificiales, conserva evidencia, detecta incompletitud/duplicidad, calcula reproduciblemente, explica calidad, separa tenants y genera reportes defendibles.