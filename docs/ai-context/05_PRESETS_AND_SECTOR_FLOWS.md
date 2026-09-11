# Carbono Zero — Presets y flujos sectoriales

## Arquitectura

Carbono Zero evolucionó hacia **núcleo ambiental común + presets por rubro**. El frontend ya soporta configuración sectorial y el backend conserva compatibilidad histórica.

## Presets documentados

### Construcción
Preset por defecto y más maduro históricamente. Flujos: combustibles, maquinaria, materiales, transporte, energía, agua, residuos, evidencias y contexto de obra.

### Aserradero / Forestal
Flujo sectorial trabajado: recepción de trozas, producción, secado, energía, transporte forestal, residuos/subproductos y biomasa cuando corresponda.

### Transporte
Configuración prevista para flota, viajes, combustible, rutas y mantenciones. La documentación antigua señalaba backend específico pendiente; verificar código actual antes de afirmar cobertura completa.

### Industrial
Configuración para energía, combustibles, procesos, residuos, agua, evidencias y factores. Verificar implementación real antes de afirmar madurez operativa.

## Validación experta

La entrevista ambiental reforzó que los flujos deben variar por rubro. Construcción destacó materiales, maquinaria, transporte, energía, combustible y residuos. Forestal destacó transporte, mecanización, uso/cambio de suelo, maquinaria, agroquímicos y residuos. Aserraderos destacó materia prima, transporte, biomasa, calderas, agua, secado y reutilización de residuos.

## Regla

Un preset configura y especializa el núcleo, pero no debe duplicar todo Carbono Zero.

## Nuevos rubros

Antes de crear uno: validar flujo real, identificar entradas/evidencia, definir datos obligatorios/opcionales, cálculo/metodología, deduplicación y calidad; recién después modelar.