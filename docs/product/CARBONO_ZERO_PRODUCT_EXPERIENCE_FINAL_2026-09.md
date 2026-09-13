# CARBONO ZERO PRODUCT EXPERIENCE — Cierre 2026-09

## Estado

Macrofase visual y de experiencia de producto completada sobre las superficies existentes, preservando contratos, permisos, rutas históricas y compatibilidad demostrada. No hubo deploy, push ni commits locales.

## Antes / después

Antes, la navegación exponía módulos internos como destinos principales y el inicio funcionaba principalmente como punto de preparación. Después, la plataforma presenta cinco destinos de producto, una navegación contextual de obra en seis áreas, un inicio de portafolio, una cabina ejecutiva por obra y un centro global de reportes.

Las superficies nuevas y refinadas usan datos reales de los servicios existentes. Los componentes de presentación no estiman impacto, readiness, riesgo, períodos ni cobertura.

## Navegación

- Global: Inicio, Obras, Reportes, Control y Configuración.
- Obra: Resumen, Operación, Gestión, Control, Reportes y Configuración.
- Operación contiene resumen operacional, energía, agua, combustibles, transporte, materiales, residuos, ruido y emisiones atmosféricas.
- Gestión contiene evidencias, problemas y acciones, cumplimiento e historial.
- Control contiene revisión profesional, gobernanza, discrepancias, expedientes y calidad.
- Reportes contiene informes, PDF, Excel, gráficos y cierre.
- Configuración contiene perfil ambiental, ámbitos, factores, metodologías y parámetros.

Activos, sensores, evidencias, importaciones, inteligencia, problemas, copiloto y gobernanza dejaron de competir como entradas globales. Sus rutas siguen disponibles para enlaces internos y compatibilidad.

## Dashboard global

`InicioPage` funciona como dashboard de portafolio y muestra obras con atención, problemas abiertos, evidencias pendientes, períodos listos, riesgos altos, prioridades y actividad reciente. Si existe una sola obra, su tarjeta ocupa el ancho disponible; si existen varias, se presenta una grilla de portafolio.

## Dashboard de obra

`ObraWorkspaceLayout` mantiene el hero con nombre, ubicación, etapa/estado, fecha y perfil. `EnvironmentalExecutiveStatus` añade período, estado ejecutivo, huella total, Alcances 1–3, evidencia, valorización, riesgo, hallazgos, readiness, descargas, distribución GEI, impacto por flujo, estado físico por flujo y recomendaciones trazables.

## Componentes y gráficos

Se consolidó un sistema reutilizable:

- `EnvironmentalDonutChart` y `EnvironmentalPieChart` para distribuciones.
- `EnvironmentalBarChart` para comparaciones por ámbito.
- `EnvironmentalTrendChart` para evolución cronológica de una misma unidad.
- `CoverageProgressChart` para readiness y cobertura.
- `ChartCard` para título, descripción, carga y estado vacío consistente.
- `FlowStatusGrid` y `AiRecommendationsPanel` para estado de flujos y recomendaciones.

Los colores de gráfico están centralizados junto a cada dominio: energía ámbar, agua azul, combustibles naranjo, transporte índigo, materiales grafito, residuos verde, ruido violeta y emisiones celeste.

## IA, problemas y acciones

Inteligencia se conserva como radar de prioridades con problemas, riesgo, anomalías, recomendaciones y acceso a acciones. El copiloto mantiene prompts sugeridos, contexto usado, respuestas estructuradas, recomendaciones y enlaces internos; no se presenta como chat genérico.

Problemas y acciones conserva el ciclo profesional desde detección hasta cierre, con severidad, responsable, fechas, progreso, evidencia, actividad y siguiente paso. Las recomendaciones de la cabina se derivan de `DiagnosticFinding`; la interfaz no inventa severidad ni explicación.

## Reportes

La ruta global `/reportes` consolida informes por obra. Presenta período, estado, readiness, cobertura, pendientes, acceso a la obra y descargas PDF/Excel generadas por el mismo motor del dashboard. Incluye búsqueda y filtros de listos/pendientes. La vista de obra conserva informe, gráficos y cierre.

## Operación y flujos

El resumen operacional responde “qué está ocurriendo físicamente” mediante ámbitos aplicables, activos, incompletos, atención, actividad reciente, cards tonales y barras por ámbito. Las vistas sectoriales comparten hero, KPIs, cobertura/calidad, cálculo, registros, sensores y evolución. La tendencia usa solo valores numéricos reales de una misma unidad y no completa períodos faltantes.

## Gobernanza y revisión profesional

Las superficies de revisión, expedientes y gobernanza existentes ya operaban como centro de control. Calidad y discrepancias incorpora hero ejecutivo y KPIs reales de discrepancias abiertas, alta severidad, evaluaciones utilizables y políticas de fuente, conservando filtros, tablas, paginación, decisiones y trazabilidad.

## Evidencias e importaciones

Evidencias mantiene tipo, flujo, estado documental, calidad/revisión, obra, origen, fechas, detalle y trazabilidad, reduciendo la lectura de simple cargador. Importaciones conserva el flujo guiado de selección, fuente/archivo, preview, interpretación, confirmación, resultado e historial, con detalle por proceso.

## Legacy

La navegación histórica fue retirada de la superficie principal, pero no se eliminaron rutas ni adaptadores con consumidores activos. Permanecen accesibles:

- `/operacion/activos` y `/operacion/sensores`, consumidos desde contextos operacionales.
- `/datos/evidencias` y `/datos/importaciones`, consumidos por accesos contextuales y configuración.
- `/inteligencia/*` y `/gobernanza/*`, consumidos desde Control, recomendaciones y enlaces internos.
- rutas de obra previas (`evidencias`, `problemas`, `timeline`, `diagnostico`, `reportes`), ahora agrupadas contextualmente.

La suite `legacyBoundary.test.js` continúa congelando los writers de compatibilidad visibles y confirma que clientes legacy sin consumidores siguen retirados. La deuda de persistencia legacy documentada en `docs/architecture/ARQ_12_LEGACY_RETIREMENT.md` no se eliminó porque todavía tiene consumidores demostrados.

## Responsive

Las superficies usan grillas fluidas y breakpoints `sm`, `md`, `lg` y `xl`: una columna en tablet estrecha, distribución progresiva en 1366 px y paneles múltiples en 1920+ px. Heroes, filtros y CTAs permiten wrap; tablas conservan sus contenedores de desplazamiento. No se buscó una experiencia móvil completa en esta macrofase.

## Verificación final

- Frontend tests: 84/84 OK, incluidos selectores nuevos de gráficos/readiness.
- Frontend lint: `npm run lint` OK.
- Frontend build: `npm run build` OK con advertencia no bloqueante por un chunk superior a 500 kB.
- Backend dashboard/reportes: 29/29 OK dentro del contenedor PostgreSQL con `--keepdb`.
- Backend check: `python manage.py check` OK.
- Migraciones: `python manage.py makemigrations --check --dry-run` sin cambios.

El intento backend desde el host falló por timeout al PostgreSQL configurado; se verificó correctamente dentro del servicio Docker saludable. El primer intento del contenedor encontró la base de test residual y fue relanzado de forma no destructiva con `--keepdb`.

## Pendientes reales

- El contrato actual no expone cobertura, revisión y discrepancias desagregadas para cada flujo; las cards no inventan esos valores.
- La generación de PDF/Excel es bajo demanda y el backend no persiste una fecha de “última generación”; el centro de reportes lo comunica explícitamente.
- Optimizar el chunk principal mayor a 500 kB mediante una macrofase posterior de partición de bundle.
- Validación visual manual con datos productivos representativos en los tres anchos objetivo antes de deploy.

## Git

- Commits locales: ninguno.
- Push: no realizado.
- Deploy: no realizado.
