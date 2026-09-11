# Carbono Zero — Motor ambiental, factores y trazabilidad

## Motor ambiental genérico

La arquitectura moderna separa interpretación de cálculo:

Operational Kernel → interpretación ambiental → contexto/flujo ambiental → elegibilidad científica → cálculo autorizado.

## Clasificación

La clasificación debe ser determinista cuando sea posible. Si no existe contexto suficiente, conservar `sin_clasificar` o `requiere_clasificacion` en lugar de adivinar.

## Construcción V1

El adaptador de construcción contempla siete flujos: combustibles, maquinaria, transporte, materiales, energía, agua y residuos. El núcleo genérico no debe hardcodear construcción.

## Factores de emisión

Tratar factores como información gobernada. Preservar fuente, versión, vigencia, unidad, categoría, alcance, estado, metadatos necesarios y relación con el cálculo.

## Cálculo reproducible

Un resultado debe poder explicar qué observaciones usó, qué metodología, qué fórmula, qué factor/versión, qué unidades/conversiones y qué resultado produjo.

## Trazabilidad objetivo

**Indicador → impacto/cálculo → metodología/factor → registro ambiental → observaciones → actividad → evidencia/versión → fuente**

## Históricos

Un cambio de factor no debe alterar silenciosamente resultados anteriores. Si se recalcula, registrar nueva versión/resultado y conservar procedencia.

## Captura completa vs elegibilidad

Son conceptos diferentes. Un flujo puede tener datos suficientes para describir la actividad pero no ser científicamente elegible por falta de factor, ambigüedad, unidad incompatible, necesidad de revisión o metodología no aprobada.