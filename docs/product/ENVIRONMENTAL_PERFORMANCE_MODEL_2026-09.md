# CARBONO ZERO — Modelo de desempeño ambiental multiflujo (2026-09)

## Filosofía

Carbono Zero dejó de tratar GEI/CO2e como sinónimo de "desempeño ambiental". GEI es una dimensión — **cambio climático** — dentro de una plataforma que gestiona energía, agua, materiales, residuos, transporte, ruido, emisiones atmosféricas y suelo. Cada flujo se lee, compara y presenta en **su propia unidad física**. Nunca se convierten unidades incompatibles a una escala común, nunca se suman kWh + m³ + kg + dB en un solo número, y nunca se fabrica una intensidad (valor/denominador) sin un denominador real y comparable en el período.

Esta refacción es de **presentación**, no de cálculo: no se tocó ninguna fórmula, motor de cálculo, migración ni contrato de API existente. Todo lo nuevo lee datos que el backend ya calcula o registra.

## Dimensiones y de dónde sale cada una

| Flujo | Fuente real | Unidad típica | Comparación período a período |
|---|---|---|---|
| Energía | `RegistroFlujoAmbiental` (`flujo=energia\|generacion_propia`) vía `/flujos-ambientales/` | kWh | Sí — agregado por mes desde `periodo_inicio` |
| Agua | `RegistroFlujoAmbiental` (`flujo=agua`) | m³ | Sí |
| Combustibles | `RegistroFlujoAmbiental` (`flujo=combustible\|combustible_movil\|combustible_estacionario`) | L | Sí |
| Residuos | `RegistroFlujoAmbiental` (`flujo=residuo`) | kg | Sí |
| Ruido | `RegistroFlujoAmbiental` (`flujo=ruido`, `metrica=laeq_diurno`) | dB(A) | Sí (no aditivo entre mediciones, pero comparable mes a mes) |
| Emisiones atmosféricas | `RegistroFlujoAmbiental` (`flujo=emisiones_atmosfericas`, sólo MP10 hoy) | µg/m³ | Sí |
| Suelo | `RegistroFlujoAmbiental` (`flujo=suelo`) | m² | Sí |
| Transporte | `ViajeOperacional` (viajes individuales, no un flujo agregado) | km, viajes | Sí — agregado por mes desde `fecha_salida` de cada viaje |
| Materiales | `EventoMaterial` / balances por material (`/obras/:id/materiales/`) | Propia por material (m³, kg, t…) | No en esta fase (ver gap) |
| GEI / Cambio climático | `CalculoAmbiental` → `ImpactoAmbiental` (derivado de energía, combustibles, transporte y materiales) | tCO2e | Sí (ya existía) |

La capa de presentación vive en [`frontend/src/features/obras/utils/environmentalPerformance.js`](../../frontend/src/features/obras/utils/environmentalPerformance.js) — pura, sin llamadas a red, testeada con 16 casos. Reutiliza `getWorkOperation` (`/flujos-ambientales/`, `/viajes-operacionales/`, `/obras/:id/materiales/`), el mismo endpoint que ya usan las páginas por flujo (`SectorDomainPage`, `TransportPage`, `MaterialsPage`, `WastePage`) — no se creó ningún endpoint nuevo.

## Reglas de presentación (aplicadas por el código, no sólo documentadas)

1. **Nunca mezclar unidades.** `buildFlowPerformance` agrupa cada flujo por mes y por unidad; si un flujo tiene mediciones en dos unidades distintas (caso raro, dato inconsistente), sólo la unidad dominante (con más meses poblados) entra al cálculo — la otra se ignora, nunca se suma.
2. **Comparación sólo cuando es real.** Un flujo sólo obtiene `hasComparison: true` si existen dos meses distintos con datos en la unidad dominante. Con un solo período, se reporta `hasComparison: false` — la UI lo muestra como "Línea de referencia", nunca como "0%" o un estado pobre.
3. **Materiales nunca se suman entre sí.** Hormigón (m³), acero (kg) y áridos (t) no se combinan en un total. `buildMaterialsPerformance` reporta sólo el material con mayor actividad, en su propia unidad, y cuenta cuántos otros materiales existen sin fusionarlos.
4. **GEI es una dimensión, nunca "el resumen".** `buildGeiPerformance` se calcula por separado y se presenta en su propio bloque "Clima / GEI"; el resto de los flujos usan `buildEnvironmentalBalance` y jamás pasan por una conversión a tCO2e.
5. **Intensidad sólo con denominador real.** Ver gap explícito más abajo — hoy no se fabrica ninguna intensidad (kWh/m², kgCO2e/m²) porque no hay un denominador poblado y comparable.

## KPIs — Dashboard de obra

**Primera capa (estado general del período):** Estado ambiental, Cobertura de datos, Cobertura de evidencia, Hallazgos críticos, Riesgo ambiental — todos ya computados por `obra_environmental_dashboard`, sin cambios de cálculo.

**Balance de flujos ambientales (nuevo):** una tarjeta por flujo con datos reales — ícono, valor + unidad propia, variación vs. el mes anterior (o "Línea de referencia" si sólo hay un período), y para transporte/materiales una nota complementaria (viajes del período / material dominante + cuántos más existen). Los flujos sin registros en el período aparecen como chips discretos, no como tarjetas vacías grandes.

**Clima / GEI (bloque propio):** Huella total, Alcance 1/2/3, donut de alcance, donut de "GEI por flujo" (renombrado desde "Distribución por flujo" para dejar explícito que mide contribución a la huella de carbono, no desempeño físico), anillos de cobertura/calidad. Incluye una nota visible (`gei.scopeCaveat`) explicando el gap de alcance descrito abajo.

## Reportes

`ReportsPage` ahora incluye una sección **"Balance de flujos ambientales"** (reutilizando el mismo `EnvironmentalBalanceSection`/`buildEnvironmentalBalance` del dashboard de obra) antes del desglose de GEI, que queda claramente delimitado bajo un separador "Cambio climático / GEI". El eje comparativo (período actual vs. anterior, `ComparisonStrip`, `ComparativeInsights`) ya existía desde la fase anterior para GEI; ahora el balance por flujo aporta la misma lógica de comparación para las demás dimensiones.

## Insights multiflujo

`pickRelevantFlows`/`buildMultiFlowNarrative` seleccionan los flujos con señal real (comparación disponible, ordenados por magnitud de variación) para la lectura ejecutiva del dashboard de obra — nunca defaultean a GEI. Ejemplo real generado por el módulo: *"La principal presión ambiental del período proviene de residuos y materiales. Residuos aumentó respecto al período anterior."* Si no hay datos físicos suficientes, el texto lo dice explícitamente en vez de inventar una lectura.

## Dashboard organizacional

Cambio de alcance limitado y honesto: el hero pasa de "Resumen ambiental" a **"Estado ambiental del portafolio"**. Los KPIs existentes (huella consolidada, obras con atención, problemas abiertos, evidencias pendientes, readiness) ya no priorizaban únicamente por CO2e (confirmado al auditar `buildPriorities`/`mapPortfolioDashboard`), así que no requerían un cambio de lógica. **No se agregaron KPIs físicos multiflujo a nivel de portafolio** porque no existe una agregación por flujo a ese nivel en el backend hoy (`organization_environmental_dashboard` sólo agrega huella/alcance/readiness/riesgo por obra) — ver gap.

## Gaps técnicos detectados (auditoría, no inventados)

- **`huella_total_tco2e` del dashboard de obra es materiales-únicamente por diseño.** `services/obra_environmental_dashboard.py` calcula el total y el split de alcance exclusivamente desde `material_ledger_totals`, y un test existente (`test_dashboard_gei_total_matches_material_ledger_directly`) lo garantiza así. Esto significa que hoy el GEI de combustibles, energía y transporte **no** está incluido en la "Huella total" ni en el split de Alcance 1/2/3 que muestra el dashboard — aunque sí es calculable (`ImpactoAmbiental.categoria` permite atribuir GEI real por flujo vía `effective_generated_ghg_impacts`). Se documenta como gap en vez de "arreglarlo" silenciosamente: cambiar qué alimenta ese total es un cambio de cálculo/contrato fuera del alcance de esta refacción de presentación, y rompería el test que lo garantiza.
- **No existe infraestructura de intensidad utilizable hoy.** El mecanismo (`IndicadorAmbiental.tipo=intensidad` + `origen_denominador` + división en `generate_indicator_value`) es real y funciona — de hecho ya lo usa `tasa_valorizacion_masa` (residuos, denominador = masa generada). Pero **no existe ningún denominador de actividad (m² construidos, HH, avance físico) poblado para el tenant de validación** (`Obra.superficie_m2` existe como campo pero el seed de 180 días no lo asigna) ni en general en el resto de seeds de producto. Por eso `buildGeiPerformance().intensity` es siempre `null` con una razón explícita (`intensityUnavailableReason`), y no se construyó ninguna tarjeta de intensidad kWh/m² ni similar. La UI queda preparada (el campo existe en el modelo de presentación) para cuando haya un denominador real.
- **Materiales sin comparación de período en esta fase.** `operation.materials` es una vista de balance (ingresos/uso/reutilización/stock) sin confirmación de que esté particionada en ventanas mensuales comparables; construir un "vs. período anterior" sobre un supuesto no verificado habría arriesgado una tendencia engañosa (prohibido explícitamente). Se deja como gap; el detalle por material con fecha real ya existe en `MaterialsPage`.
- **Emisiones atmosféricas: sólo MP10 existe hoy.** El campo `metrica` es de texto libre (no un enum), así que agregar PM2.5/NOx/SO2/COV no requiere migración — pero no hay datos ni factor alguno para ellos hoy; no se inventaron.
- **Ruido: sin excedencias.** No existe un límite/umbral gobernado en el sistema para ruido — la UI nunca muestra un estado de "excedencia" para este flujo, tal como pide el brief ("sólo cuando exista un límite aplicable gobernado").
- **Cobertura/evidencia no es genérica para todos los flujos.** `build_period_readiness` (la fuente de los anillos "Calidad y trazabilidad") está hoy acotada a energía/agua/combustible/residuos/materiales para cobertura de registros, y a materiales específicamente para evidencia/factores — ruido, emisiones atmosféricas y suelo no participan de este cálculo de readiness todavía. La trazabilidad genérica (`Observacion.evidencia` + `EvaluacionCalidadDato`) sí es agnóstica de flujo y ya existe; extender el agregado de readiness a los 3 flujos restantes es trabajo de backend fuera de esta fase.
- **Portafolio sin rollup físico por flujo.** `organization_environmental_dashboard` no agrega energía/agua/residuos/materiales físicos entre obras — sólo huella, alcance, readiness y riesgo. Construir KPIs físicos consolidados a nivel de portafolio requeriría un endpoint nuevo (fuera de "reutilizar servicios existentes" para esta fase).
- **Riesgo conocido, no de esta fase:** el bug de `material_ledger.ledger_entries` (filtra por `CalculoAmbiental.fecha_calculo`, no por la fecha del evento de recepción) ya estaba documentado en `docs/seed-showcase-180d.md`; puede hacer que el GEI histórico de materiales aparezca en cero para meses pasados aunque existan recepciones y cálculos trazables. No se tocó — corregirlo es un cambio de selector de dominio fuera de esta refacción.

## Validación visual

**Docker Desktop no estuvo disponible en este entorno** (se intentó iniciar repetidamente, sin éxito) — no fue posible levantar el backend ni ejecutar `seed_showcase_180d` para validar contra el tenant `DEMO_HORIZONTE` real. La validación se hizo con un arnés temporal (`qa-preview.html`/`.jsx`, eliminado por completo al terminar, sin rastro en el árbol de trabajo) que renderizó los componentes reales (`EnvironmentalBalanceSection`, KPIs, narrativa) contra datos sintéticos con la misma forma que el backend (`RegistroFlujoAmbiental`-shaped records, viajes con fechas reales, balances de materiales), cubriendo: múltiples flujos con datos, un solo período (sin comparación), flujo sin datos, y materiales con múltiples unidades. **Pendiente**: re-validar contra el seed real de 180 días en cuanto Docker esté disponible — el mapa de campos usado (`periodo_inicio`, `mediciones[].{concepto,valor,unidad}`, `fecha_salida`, `metricas.distancia_km`, `ingresos_periodo`) proviene de dos auditorías de código exhaustivas con cita de archivo:línea, pero no de una ejecución real contra la base de datos.

## Archivos nuevos/modificados

- `frontend/src/features/obras/utils/environmentalPerformance.js` (nuevo) + `.test.js` (16 tests)
- `frontend/src/features/obras/components/EnvironmentalBalanceSection.jsx` (nuevo)
- `frontend/src/features/obras/pages/ObraResumenPage.jsx` (reorganizado)
- `frontend/src/features/obras/pages/ObraResumenPage.test.js` (actualizado)
- `frontend/src/app/layouts/ObraWorkspaceLayout.jsx` (fetch de `operation` en resumen y reportes)
- `frontend/src/features/reportes/pages/ReportsPage.jsx` (sección de balance + separador GEI)
- `frontend/src/features/inicio/pages/InicioPage.jsx` (hero reencuadrado)
