# Carbono Zero — Arquitectura y stack

## Arquitectura vigente

Carbono Zero utiliza backend Django/DRF, frontend React/Vite y una arquitectura de dominio que evolucionó desde modelos legacy de construcción hacia componentes modernos y genéricos.

## Backend confirmado

Dependencias relevantes actuales: Django 6.0.4, DRF 3.17.1, PostgreSQL vía psycopg 3, pandas, openpyxl, OpenAI SDK, numpy, scikit-learn, pypdf, python-docx, reportlab, Resend, requests y defusedxml.

Apps visibles: `apps.analytics`, `apps.iot`, `apps.knowledge`.

## Frontend confirmado

React 19.2.5, React Router 7, Vite 8, Tailwind 4, Axios, Recharts, Leaflet, Framer Motion y Lucide React.

## Dirección arquitectónica

La documentación ARQ formaliza la separación:

Platform / Tenant / RBAC → Operational Context → Operational Kernel → Capture/Ingestion → Environmental Interpretation → Scientific Eligibility → Calculation → Quality / Improvement → Reporting.

## Legacy vs moderno

Existen modelos y endpoints históricos compatibles. No eliminarlos ni promoverlos como fuente canónica moderna sin revisar documentos ARQ.

Regla: preservar compatibilidad, evitar nuevas dependencias hacia legacy y migrar de forma explícita.

## No sobrearquitecturar

No introducir microservicios, event sourcing, buses u otra complejidad distribuida sin necesidad real. Priorizar invariantes, trazabilidad, claridad de dominio, seguridad multi-tenant, cálculo reproducible y auditabilidad.