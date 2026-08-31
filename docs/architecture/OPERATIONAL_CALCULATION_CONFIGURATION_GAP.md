# Brecha de configuración del cálculo operacional

El mensaje “No existe una metodología activa y vigente configurada para esta actividad” es correcto cuando `select_methodology()` no encuentra candidatos gobernados. Este correctivo documental no agrega factores ni altera el cálculo.

Para habilitar Combustibles debe existir, de forma coherente y vigente:

1. una `MetodologiaAmbiental` activa cuyo flujo aplique a `combustible`, `combustible_movil` o `combustible_estacionario`;
2. una `VersionMetodologia` en estado `activa`, dentro de vigencia y con aplicabilidad compatible con el tipo de actividad;
3. su `FormulaCalculo` y las `VariableFormula` que resuelvan la observación `combustible_consumido`, con unidad esperada explícita;
4. un `FactorAmbiental` compatible con el combustible y la clasificación móvil/estacionaria;
5. una `VersionFactorAmbiental` activa y vigente, con unidad de entrada convertible desde la unidad observada y unidad de resultado definida.

`import_huellachile_factors` carga el catálogo y versiones de factores, pero actualmente no crea la metodología, fórmula ni variables requeridas. Por tanto, ejecutar solo ese importador no cierra la configuración. La carga gobernada de metodología debe resolverse en un cambio separado, con fuente, versión, vigencia y revisión profesional definidas; no mediante valores hardcodeados en UI o en el flujo documental.
