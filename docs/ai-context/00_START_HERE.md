# Carbono Zero — AI Context Canonical

**Proyecto:** Carbono Zero  
**Empresa:** Mundaca's Solutions SpA  
**Repositorio principal:** `cristobalMundacaV/proyecto-huella`  
**Rama canónica:** `main`  
**Corte de auditoría:** 2026-09-11

Este directorio entrega contexto actualizado para asistentes de IA. No reemplaza el código ni los contratos técnicos vigentes.

## Orden de lectura

1. `01_PRODUCT_AND_DOMAIN.md`
2. `02_ARCHITECTURE_AND_STACK.md`
3. `03_OPERATIONAL_KERNEL_AND_CAPTURE.md`
4. `04_ENVIRONMENTAL_ENGINE_FACTORS_AND_TRACEABILITY.md`
5. `05_PRESETS_AND_SECTOR_FLOWS.md`
6. `06_EVIDENCE_DATA_QUALITY_AND_DEDUPLICATION.md`
7. `07_AI_IOT_AND_KNOWLEDGE.md`
8. `08_TENANCY_RBAC_SECURITY.md`
9. `09_DEPLOYMENT_TESTING_OPERATIONS.md`
10. `10_CURRENT_STATUS_AND_ROADMAP.md`
11. `11_CLAUDE_WORKING_RULES.md`

## Regla de precedencia

Ante conflicto: instrucción más reciente de Cristóbal → código/configuración actual de `main` → `docs/ai-context/` → documentación ARQ reciente → documentación histórica → README/pitches.

## Advertencia

El README raíz todavía describe Carbono Zero principalmente como plataforma para constructoras. Esa descripción es histórica pero incompleta: el producto evolucionó hacia un núcleo ambiental genérico con presets sectoriales y Operational Kernel formalizado.

## Principio rector

Carbono Zero debe adaptarse al flujo ambiental real de la empresa. No debe inventar datos, mezclar tenants/obras/workspaces, usar IA como fuente de verdad, recalcular históricos silenciosamente ni contabilizar dos veces una misma actividad representada por varias fuentes.