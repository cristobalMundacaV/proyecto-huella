# Carbono Zero — Operational Kernel y captura

## Operational Kernel

El núcleo operacional registra lo que ocurrió en la operación antes de interpretar impacto ambiental.

Entidades canónicas importantes: `FuenteDatos`, `ActividadOperacional`, `Observacion`, `ActivoOperacional`, `UnidadOperacional`, `ProcesoOperacional`, `Obra`, `AreaOperacional`, `EspacioTrabajoOperacional`, `EvidenciaObra` y `VersionEvidencia`.

## Principio

**Observacion es el dato atómico.** `ActividadOperacional` aporta contexto/evento y la evidencia aporta procedencia documental. Ninguno de estos elementos por sí solo decide impacto, cumplimiento, factor, metodología o resultado ambiental.

## Captura unificada

Los canales modernos convergen hacia el mismo núcleo: manual, importación estructurada, archivos tabulares, documentos, API, sensores/IoT, flujos sectoriales, transporte y materiales.

La captura debe preservar organización, fuente, concepto, timestamp, valor, método, naturaleza, estado, actor, evidencia, versión exacta y registro extraído cuando aplique.

## Estados y verdad

Una observación pendiente no equivale a dato verificado. AI/extracción/clasificación sugerida no se convierte automáticamente en verdad.

## Invariantes

- tenant consistente en todas las relaciones;
- versión pertenece a evidencia;
- obra/contexto pertenecen a la organización;
- valores cumplen contrato;
- no inventar datos faltantes;
- mutaciones críticas transaccionales.

## Regla de ingeniería

No crear directamente resultados ambientales desde una carga de archivo. Primero capturar hecho/procedencia; luego interpretar; luego calcular.