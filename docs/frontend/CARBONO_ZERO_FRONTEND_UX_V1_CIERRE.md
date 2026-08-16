# Carbono Zero — Cierre Frontend UX V1

Estado: **CERRADO**.

La arquitectura frontend autoritativa es `app/features/shared/presets`, acompañada por `assets` y `styles`. `core/factores` permanece como excepción gobernada y sin autoridad paralela.

Principios verificados:

- backend como autoridad de permisos, ciencia y persistencia;
- URL como autoridad de organización, obra y recurso;
- obra como límite operacional;
- trazabilidad desde dato hacia fuente y evidencia disponible;
- IA consultiva, nunca autoridad de decisión;
- cálculos determinísticos y resultados históricos versionados;
- error distinto de vacío;
- cero distinto de dato ausente;
- aislamiento tenant contractual y visual.

QA de cierre: ESLint, build productivo, diff check, rutas profundas, navegación, responsive, estados asíncronos, demo read-only y auditoría UX de accesibilidad. No representa certificación WCAG ni auditoría formal de seguridad.

Deuda posterior: pruebas E2E con navegador real, auditoría formal con tecnologías asistivas y optimización adicional basada en medición de producción.
