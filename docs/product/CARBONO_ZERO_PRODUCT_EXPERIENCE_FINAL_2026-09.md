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

## UNIFIED CONTEXT EXPERIENCE (2026-09, macrofase de unificación)

### Arquitectura anterior

Carbono Zero se sentía como dos aplicaciones: un sidebar organizacional (Inicio/Obras/Reportes/Control/Configuración) y, al entrar a una obra, un `WorkSidebar` completamente distinto con seis grupos (Resumen/Operación/Gestión/Control/Reportes/Configuración) y ~20 destinos propios. Cambiar de "vista organizacional" a "vista de obra" se sentía como cambiar de producto.

### Arquitectura nueva

Un solo sidebar (`Sidebar.jsx` → `GeneralNavigation`) con **un único conjunto de cinco destinos** — Inicio, Obras, Reportes, Control, Configuración — cuyo *target* cambia según el contexto seleccionado, en vez de un segundo menú. La fuente de verdad es `getUnifiedNavigation({ preset, scope })` en `app/navigation.js`: `scope` es `{ type: "portfolio" }` o `{ type: "obra", obraId }`, derivado directamente de la URL (igual que antes, sin estado nuevo que sincronizar). `getWorkNavigation` y el componente `WorkSidebar` fueron eliminados; no queda un segundo árbol de navegación en ningún punto del código.

| Destino | Portafolio | Obra |
|---|---|---|
| Inicio | `/inicio` (dashboard de portafolio) | `/obras/:id/resumen` (cabina de obra, sin cambios) |
| Obras | `/obras` (sin cambios en ningún contexto) | `/obras` |
| Reportes | `/reportes` (centro global) | `/obras/:id/reportes` (informe de la obra, reutilizado, no duplicado) |
| Control | `/gobernanza` (sin cambios) | `/obras/:id/control` (hub nuevo) |
| Configuración | `/administracion` (sin cambios) | `/obras/:id/configuracion` (hub nuevo) |

La navegación profunda de obra (energía, agua, combustibles, transporte, materiales, residuos, ruido, emisiones atmosféricas, evidencias, problemas, cumplimiento, historial) **no desapareció**: vive como tarjetas/enlaces dentro de `OperacionOverviewPage`, la cabina de obra y los dos hubs nuevos — nunca como una entrada de sidebar adicional.

### Selector de contexto

`ContextSelector` (nuevo, dentro de `Sidebar.jsx`) reemplaza la etiqueta "perspectiva organizacional" por un desplegable explícito: **Portafolio** o el nombre de cada obra. Seleccionar una obra navega a `/obras/:id/resumen` (o preserva la sub-ruta actual si ya se estaba en otra obra); seleccionar Portafolio vuelve a `/inicio`. No introduce estado propio: la obra activa sigue siendo la que indica la URL.

### Dashboard Portafolio (nuevo motor backend)

`apps/analytics/services/organization_environmental_dashboard.py` agrega el mismo motor por obra (`build_obra_dashboard`) sobre cada obra visible para el usuario (`filter_works_for_user`, la misma función RBAC que ya usaba `/obras/`) — nunca una fórmula nueva, sólo sumas/promedios/rankings sobre dashboards ya calculados. Expuesto en `GET /organizaciones/<id>/dashboard-portafolio/` (mismo patrón `_scope`/`_period_params` que `views_obra_dashboard.py`). Devuelve huella total y por alcance, impacto por flujo, emisiones/readiness/riesgo por obra, hasta 5 "obras prioritarias" (rankeadas por riesgo + hallazgos + brecha de readiness) y **máximo 3 insights** (`_portfolio_insights`, cada uno derivado de un número ya presente en los dashboards, nunca texto libre).

`InicioPage` consume este único endpoint (`getOrganizationDashboard`) en vez de sumar N dashboards por obra en el frontend — se eliminó ese bucle N+1 client-side (`buildPortfolioImpact`) y se reemplazó por `mapPortfolioDashboard`, un transform puro y testeado. La página ahora muestra: hero verde petróleo con huella/readiness consolidados, dos filas de KPIs, cuatro gráficos (GEI por alcance, distribución por flujo, emisiones por obra, readiness por obra), una sección "Obras prioritarias" (ranking real) y un bloque "Prioridades de la organización" con los insights (máximo 3) del backend.

### Dashboard de obra

Sin cambios de fondo — se mantiene `WorkExecutiveDashboard` (hero, lectura ejecutiva, KPIs, donas, readiness, estado por flujo, recomendaciones) tal como ya estaba construido; sólo se integra en la arquitectura unificada como el destino "Inicio" del contexto de obra.

### Control y Configuración de obra (hubs nuevos, no duplicados)

`WorkControlPage` (`/obras/:id/control`) y `WorkConfigPage` (`/obras/:id/configuracion`) son páginas delgadas que reutilizan datos ya cargados por `ObraWorkspaceLayout` (cumplimiento, contexto) y enlazan a las superficies existentes de gobernanza/revisión/discrepancias/expedientes y a `/administracion/ambiental`, `/gobernanza/factores`, `/administracion/calculo`. No se reimplementa ninguna lógica de esas páginas — es honesto sobre que el filtrado por obra en esas superficies globales sigue pendiente (ver Pendientes).

### Rutas legacy

Ninguna ruta fue eliminada. `getWorkNavigation` sí se eliminó de `navigation.js` (sin consumidores fuera de `Sidebar.jsx`, que fue reescrito); todas las rutas que ese menú exponía (`/obras/:id/operacion/*`, `/evidencias`, `/problemas`, `/timeline`, `/cumplimiento`, `/reportes`) siguen registradas en `router.jsx` y accesibles por enlace interno.

### Tests

- `app/navigation.test.js` (nuevo): portafolio vs. obra apuntan a las rutas correctas, un solo grupo de navegación en ambos casos, fallback de obra sin id, `getPageContext` resuelve los dos hubs nuevos.
- `features/inicio/utils/portfolioSelectors.test.js` (nuevo): shape vacío sin throw, mapeo completo, tope de 3 insights incluso si el backend enviara más, un alcance en cero no genera una porción falsa en la dona.
- `apps/analytics/test_organization_environmental_dashboard.py` (nuevo, backend): el total agregado coincide con la suma de los dashboards por obra, `obras_activas` respeta lo visible al usuario, nunca más de 3 insights ni de 5 obras prioritarias, determinismo, un tenant sin obras no rompe, aislamiento entre tenants, RBAC `alcance=OBRAS` sólo agrega la obra asignada, autenticación/permiso requeridos.

### Pendientes reales (agregado a los ya documentados arriba)

- Control y Configuración de obra son hubs de enlace, no filtros reales: las páginas globales de gobernanza/revisión/discrepancias/expedientes no reciben todavía un parámetro de obra.
- `ReportsCenterPage` sigue construyendo su tabla con un `Promise.allSettled` por obra (`getReportsCenterOverview`) en vez de leer del nuevo agregador de portafolio; es correcto (cada fila es el dashboard real de esa obra) pero podría simplificarse reutilizando `readiness_por_obra`/`emisiones_por_obra` del nuevo endpoint.
- El agregador de portafolio procesa hasta 30 obras por organización (`MAX_WORKS_AGGREGATED`); una organización con más obras vería el resto omitido de forma silenciosa-pero-documentada, no fabricada.

## Git

- Commits locales: ninguno.
- Push: no realizado.
- Deploy: no realizado.
