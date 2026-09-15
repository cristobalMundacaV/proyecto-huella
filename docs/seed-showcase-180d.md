# Showcase sintético de construcción — 180 días

El comando `seed_showcase_180d` amplía sólo el tenant `DEMO_HORIZONTE` (Constructora Horizonte Demo SpA). Reutiliza la base de obras, materiales y factores gobernados del seed de IA, pero no ejecuta su historia antigua ni sus valores de indicador prefijados. Los nuevos resultados de cálculo se obtienen con `calculate_activity`; los indicadores mensuales con `generate_indicator_value`. Los factores adicionales de materiales son sintéticos, están marcados como tales y transitan el flujo de gobernanza real. Nunca son referencias oficiales.

## Crear, repetir y verificar

Desde `backend/`, en una base de desarrollo aislada:

```text
python manage.py seed_showcase_180d --end-date 2026-09-15
python manage.py seed_showcase_180d --end-date 2026-09-15
python manage.py seed_showcase_180d --verify-only
```

La primera ejecución guarda la fecha de término en `onboarding_data.showcase_180d_end`. Las siguientes usan esa ancla aunque se omita `--end-date`; una fecha diferente falla sin borrar datos. No hay `--reset` destructivo: cálculos, mapeos y evidencia gobernada son históricos e inmutables; repetir el comando es la regeneración segura. Para un tenant totalmente nuevo, usar una base demo nueva, no eliminar manualmente el tenant existente.

El comando imprime conteos de organizaciones/obras, usuarios, activos, puntos de infraestructura, sensores, lecturas, mantenimientos, actividades por flujo, documentos, alertas, evidencias, problemas, acciones, revisiones, discrepancias, expedientes, cálculos y período. Las cuentas demo creadas tienen contraseñas inutilizables; el comando no publica credenciales de acceso. Para probar RBAC, asignar contraseñas sólo en un entorno aislado mediante el procedimiento de administración normal, sin ponerlas en el repositorio. Un administrador, un responsable ambiental, un operador limitado a Norte, un analista limitado a Sur, un revisor y un lector usan los roles y `UsuarioObraAcceso` reales.

## Historia y cobertura

Norte tiene diagnóstico completo y 180 días; Sur tiene cobertura media y diagnóstico en progreso; Centro Logístico Biobío tiene menos datos y aplicabilidad pendiente. Las lecturas finales cubren exactamente 180 días. Combustible y viajes dominan instalación de faena; hormigón, acero y áridos aumentan en fundaciones/estructura; energía y agua crecen en instalaciones; residuos diversos aparecen en terminaciones. Ruido, MP10 y suelo son controles periódicos, no filas idénticas diarias. Hay mantenimiento realizado, programado y vencido; sensores operativos y fuera de servicio; evidencia validada, pendiente y observada; una discrepancia; hallazgos profesionales; problemas abiertos/cerrados y expedientes en revisión.

La capa moderna de transporte se representa con `ViajeOperacional`, ruta, vehículo y observaciones seleccionadas; materiales con `EventoMaterial`; los demás flujos soportados con `RegistroFlujoAmbiental`. El catálogo de onboarding selecciona diez aspectos aplicables, con relaciones a áreas reales. El seed no fabrica porcentajes de cumplimiento, umbrales normativos ni reportes calculados. Los documentos y alertas de cumplimiento son controles documentales internos sintéticos, no afirmaciones legales.

## Superficies para revisión visual

Con la organización demo seleccionada, revisar `/inicio`, `/obras`, `/obras/{id}/resumen`, las rutas `/obras/{id}/operacion/*` (energía, agua, combustibles, transporte, materiales, residuos, ruido, emisiones atmosféricas, suelo), `/obras/{id}/evidencias`, `/obras/{id}/problemas`, `/obras/{id}/cumplimiento`, `/obras/{id}/control`, `/obras/{id}/configuracion`, `/obras/{id}/reportes`, `/reportes`, `/activos`, `/activos/flota`, `/activos/equipos`, `/activos/sensores`, `/activos/mantenciones`, `/gobernanza/revision`, `/gobernanza/calidad`, `/gobernanza/expedientes` y `/administracion/equipo`.

La infraestructura se inspecciona mediante activos y puntos ambientales; no existe una ruta dedicada a infraestructura en el router actual. `/datos/importaciones` seguirá sin cargas de importación porque el showcase no inventa ejecuciones de ingestión. Tampoco se fuerza un informe formal: los indicadores físicos sí tienen meses consecutivos comparables. Las rutas de gobernanza siguen siendo organizacionales, aunque las referencias seeded apunten a problemas de obras demo.

## Validación

Estado legacy descubierto: `material_ledger.ledger_entries` filtra GEI por `CalculoAmbiental.fecha_calculo`, no por la fecha del evento de recepción. Al calcular hoy una historia de 180 días, el GEI de meses pasados puede mostrarse en cero aunque existan recepciones y cálculos trazables. El showcase conserva la fecha de cálculo auditada y no la altera para maquillar reportes. La comparación histórica de GEI requiere una corrección de selector de dominio fuera del alcance del seed; hasta entonces, los indicadores de consumos físicos son la comparación temporal verificable.

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.analytics.test_seed_showcase_180d
```

Para pruebas locales con SQLite, fijar `DATABASE_ENGINE=django.db.backends.sqlite3` sólo en el proceso de test. Nunca ejecutar el seed de escritura contra producción: modifica `DEMO_HORIZONTE` y no está diseñado para clientes reales.
