# Carbono Zero — Evidencia, calidad del dato y deduplicación

## Evidencia

La evidencia debe demostrar de dónde salió un dato. Puede ser factura, boleta, guía, ticket de pesaje, certificado, informe, telemetría, lectura instrumental, archivo o API.

## Versiones

`VersionEvidencia` conserva versión y checksum. La versión exacta utilizada debe poder asociarse a la observación/proceso. No sustituir silenciosamente un archivo histórico.

## Calidad del dato

Diferenciar, como mínimo, medición primaria, evidencia documental, registro interno y estimación. No presentar una estimación con la misma confianza que una medición.

## Validación humana

La entrevista con especialista indicó que una persona capacitada debe validar parámetros relevantes. AI puede asistir, no aprobar verdad por defecto.

## Duplicidad

Una misma actividad puede aparecer en combustible, kilometraje, GPS, guía, factura y hoja de ruta. No sumar automáticamente todo.

## Estrategia segura

Usar identificadores y reglas gobernadas: checksum, referencia externa, periodo, entidad, actividad, documento, confirmación y semántica. No hacer fuzzy merge como fuente de verdad sin revisión.

## Conflictos

Si dos fuentes discrepan, conservar ambas, registrar procedencia, señalar conflicto y aplicar prioridad solo si existe regla validada.

## Materiales

La validación experta destacó distinguir material comprado de material realmente utilizado.

## Residuos

Evidencias relevantes: ticket de pesaje, guía de retiro y certificado de disposición/valorización. Preservar destino y tratamiento.