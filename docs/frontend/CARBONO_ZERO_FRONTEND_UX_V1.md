# Carbono Zero — Arquitectura Frontend UX V1

## 1. Alcance y estado auditado

- Fase: UX-01, análisis y decisión arquitectónica. No inicia UX-02.
- Commit auditado: `80e445aecc0494f341be4f928e70cd3d422d9906` (`correctivo fase 17`).
- Runtime modificado: ninguno.
- Universo: `src/app`, `core`, `domain`, `features`, `layouts`, `presets`, `shared`, `styles`, `assets`, `landing`, `main.jsx`, Vite, ESLint y `package.json`.
- Tamaño: 187 archivos JSX; 42 archivos que representan páginas/vistas; 33 estados de pantalla alcanzables (incluye landing, login, verificación, selección inicial, 24 vistas reales de `ActiveView` y 5 placeholders).

La aplicación funciona como SPA React/Vite con una selección manual de vistas, no como aplicación enrutada. `Root` sólo distingue landing (`/`), verificación pública (`/verificar/*`) y aplicación autenticada. Dentro de la aplicación, `App.jsx` mantiene `activeView`; el objeto `appRoutes` existe, pero no gobierna el render ni la URL.

## 2. Problemas arquitectónicos comprobados

1. `App.jsx` mezcla guardas de autenticación, resolución de organización/preset, shell responsive, navegación, transiciones y registro de páginas.
2. La URL no expresa la pantalla, organización ni obra; refresh, deep-link, back/forward y compartir contexto no funcionan correctamente.
3. `app/routes.jsx` es un registro parcial y desconectado, creando una segunda representación incompleta de navegación.
4. `core/` y `features/` contienen el mismo tipo de artefactos. Evidencias, factores, importaciones y reportes tienen implementaciones paralelas.
5. Los presets de aserradero contienen páginas completas; construcción/transporte/industrial son principalmente configuración. El comportamiento no es uniforme.
6. La obra se abre dentro de modal/estado local de `ObrasPage`; no existe workspace direccionable aunque construcción define Obra como frontera primaria.
7. `OperacionPage` agrega Activity Core, transporte, materiales y flujos a nivel organización; debe poder recibir scope de obra.
8. Funciones técnicas (`factores`, `etapas`, ingesta, acciones) aparecen como destinos planos o están ocultas/desconectadas, sin jerarquía de producto.
9. `shared/services/api.js` es un cliente y también un catálogo monolítico de endpoints, aliases legacy, simulaciones locales y stubs. Convive con servicios por feature.
10. Hay dos accesos `fetch` directos (`RouteMapPicker`, `ImportarEvidenciaObraModal`) fuera del cliente HTTP.
11. No existe estado global de obra activa; la selección vive localmente en Obras. Auth y organización sí tienen providers adecuados.
12. Hay duplicación visual en KPI cards, tablas/paginación, hero/page headers, modales, badges, empty states y paneles.
13. Tailwind utility classes, variables CSS y estilos especializados conviven con colores, sombras y radios hardcodeados.
14. Existen páginas placeholder/desconectadas y archivos vacíos o muy parciales que aparentan funcionalidad.

## 3. App.jsx: responsabilidades

Responsabilidades correctas en la capa `app`: bootstrap de providers, guardas de sesión, selección de layout autenticado y boundary de carga/error. Deben salir de `App.jsx`: registro `ActiveView`, `activeView`, navegación móvil, resolución de menú preset, señal imperativa para crear organización y imports de páginas. El layout debe contener Navbar/Sidebar; el router debe resolver páginas, redirects, parámetros y transiciones. La ausencia de organización será una ruta/guarda de onboarding, no una variante profunda del componente raíz.

## 4. Inventario de vistas

`Backend` identifica la familia consumida; los componentes hijos pueden ampliar sus llamadas. “Desconectada” significa que no existe camino desde `Root/App/Sidebar`.

| Vista actual | Archivo / feature | Propósito y scope | Backend principal | Estado | Destino y acción |
|---|---|---|---|---|---|
| Landing | `landing/CarbonoZeroLanding.jsx` | Comercial, público | Ninguno | Funcional | `/`; CONSERVAR y mover ownership a `features/public` o mantener landing explícita |
| Login/bootstrap | `features/auth/pages/LoginPage.jsx` | Sesión, público | `/auth/*` | Funcional | `/login`; CONSERVAR |
| Verificar obra | `features/obras/pages/VerificarObra.jsx` | Ficha pública de obra | `/verificar/obra/:codigo` | Funcional | `/verificar/:codigo`; CONSERVAR |
| Dashboard | `core/dashboard/DashboardPage.jsx` | Inicio ejecutivo, organización | dashboard, KPIs, IoT, escenarios | Funcional | `/inicio`; MOVER a `features/inicio` |
| Diagnóstico ambiental | `features/diagnostico/pages/DiagnosticoAmbientalPage.jsx` | Diagnóstico/capacidades, organización | diagnóstico, unidades, procesos | Funcional | `/administracion/diagnostico`; MOVER |
| Operación | `features/operacion/pages/OperacionPage.jsx` | Actividades, transporte, materiales, flujos | Activity Core, calculation, transport/material/sector APIs | Funcional, scope org | `/obras/:obraId/operacion`; REESCRIBIR composición para scope obra, conservar feature panels |
| Activos | `features/activos/pages/ActivosPage.jsx` | Activos/mantenimiento, organización | `/organizaciones/:id/activos/*` | Funcional | `/operacion/activos`; CONSERVAR/MOVER ruta |
| Sensores | `features/sensores/pages/SensoresPage.jsx` | Dispositivos, instalaciones, calibración, lecturas | sensores V2 | Funcional | `/operacion/sensores`; CONSERVAR/MOVER ruta |
| Inteligencia | `features/intelligence/pages/IntelligencePage.jsx` | Resumen inteligente y acciones trazables | intelligence/context/actions | Funcional | `/inteligencia`; CONSERVAR |
| Copiloto | `core/copiloto/pages/CopilotoAmbientalPage.jsx` | Contexto/propuestas, organización/problema | Copiloto v2 | Funcional | `/inteligencia/copiloto`; MOVER a `features/copiloto` |
| Acciones | `features/acciones/pages/AccionesAmbientalesPage.jsx` | Problemas, acciones, evidencia/cierre | problems/actions/environmental documents | Funcional | `/inteligencia/acciones`; CONSERVAR; dentro de obra filtrar scope |
| Evidencias | `features/evidencias/pages/EvidenciasPage.jsx` | Evidencias e ingesta, organización | evidencias + ingestion V2 | Funcional | `/datos/evidencias`; CONSERVAR |
| Administración | `features/administracion/pages/AdministracionPage.jsx` | Hub administración | composición org/users/config | Funcional | `/administracion`; CONSERVAR como índice, no duplicar páginas |
| Organizaciones | `features/organizaciones/pages/OrganizacionesPage.jsx` | CRUD/selección organización | `/organizaciones/*` | Funcional | `/administracion/organizacion`; MOVER |
| Obras | `features/obras/pages/ObrasPage.jsx` | Listado, creación y detalle modal | obras, registros, evidencia, transporte legacy | Funcional con detalle acoplado | `/obras`; CONSERVAR listado; REESCRIBIR detalle como workspace |
| Detalle de obra | `features/obras/components/ObraDetailView.jsx` | Tabs de ficha, resumen, emisiones, evidencia, historia | endpoints por obra | Funcional, embebida | `/obras/:obraId/*`; MOVER y dividir por rutas hijas |
| Etapas | `features/etapas/pages/EtapasPage.jsx` | Estructura/etapas, organización | etapas | Funcional | `/administracion/estructura`; FUSIONAR con estructura operacional |
| Factores | `features/factores/pages/FactoresPage.jsx` | Catálogo legacy/V2 | factores/metodologías | Funcional | `/gobernanza/factores`; CONSERVAR y separar tabs gobernados |
| Importaciones | `features/importaciones/pages/ImportacionesPage.jsx` | Importadores legacy + ingestion V2 | preview/confirm/ingestion | Funcional | `/datos/importaciones`; CONSERVAR, migrar autoridad a ingestion V2 progresivamente |
| Usuarios | `features/usuarios/pages/UsuariosPage.jsx` | Miembros de organización | `/organizaciones/:id/usuarios` | Funcional | `/administracion/usuarios`; CONSERVAR |
| Configuración | `features/configuracion/pages/ConfiguracionPage.jsx` | Config org/metodologías | configuración, metodologías | Funcional | `/administracion/configuracion`; FUSIONAR panel metodológico con gobernanza |
| Reportes regulatorios | `core/reportes-regulatorios/pages/ReportesRegulatoriosPage.jsx` | Estado regulatorio/ejecutivo | reports, actions summary | Funcional | `/gobernanza/informes`; MOVER a `features/reportes` |
| Recepción trozas | `presets/aserradero/pages/RecepcionTrozasPage.jsx` | Operación aserradero | wrapper/config compartida | Funcional sectorial | `/operacion/recepcion-trozas`; FUSIONAR en renderer operacional configurable |
| Producción aserradero | `presets/aserradero/pages/ProduccionAserraderoPage.jsx` | Operación aserradero | wrapper/config | Funcional sectorial | `/operacion/produccion`; FUSIONAR |
| Secado aserradero | `presets/aserradero/pages/SecadoAserraderoPage.jsx` | Operación aserradero | wrapper/config | Funcional sectorial | `/operacion/secado`; FUSIONAR |
| Energía aserradero | `presets/aserradero/pages/EnergiaAserraderoPage.jsx` | Flujo energía | wrapper/config | Funcional sectorial | workspace/operación energía; FUSIONAR |
| Transporte forestal | `presets/aserradero/pages/TransporteForestalPage.jsx` | Flujo transporte | wrapper/config | Funcional sectorial | workspace/operación transporte; FUSIONAR |
| Residuos/subproductos | `presets/aserradero/pages/ResiduosSubproductosPage.jsx` | Flujo residuos | wrapper/config | Funcional sectorial | workspace/operación residuos; FUSIONAR |
| Lotes forestales | `presets/aserradero/pages/LotesForestalesPage.jsx` | Lotes/transporte forestal | lotes forestales | Funcional sectorial real | `features/materiales-forestales`; MOVER, preset sólo registra capacidad |
| Flota/Viajes/Combustible/Rutas/Mantenciones | inline `placeholderViews` | Promesa de módulos transporte | Ninguno | Placeholder (5) | RETIRAR_DE_NAVEGACION hasta conectar features reales; ELIMINAR_AL_FINAL |
| Reportes features | `features/reportes/pages/ReportesPage.jsx`, `ReportesView.jsx` | Skeleton/alias | Ninguno o componentes stub | Parcial/desconectada | FUSIONAR en `features/reportes`; eliminar wrappers vacíos |
| Reportes core | `core/reportes/pages/ReportesPage.jsx` | Reportería ejecutiva | dashboard/registros/actions | Funcional/desconectada de App | FUSIONAR con reportes regulatorios e informes de obra |
| Evidencias core | `core/evidencias/pages/EvidenciasPage.jsx` | Experiencia documental alternativa | compliance/evidence | Duplicada/desconectada | FUSIONAR en feature evidencias; ELIMINAR_AL_FINAL |
| EvidenciasView | `features/evidencias/pages/EvidenciasView.jsx` | Wrapper/variante | evidencia | Duplicada/desconectada | ELIMINAR_AL_FINAL tras verificar imports |
| Factores core | `core/factores/pages/FactoresPage.jsx` | Experiencia catálogo alternativa | factores | Duplicada/desconectada | FUSIONAR en gobernanza; ELIMINAR_AL_FINAL |
| Importaciones core | `core/importaciones/pages/ImportacionesPage.jsx` | Experiencia import alternativa | import config | Duplicada/desconectada | FUSIONAR en feature importaciones |
| Ingesta inteligente | `core/ingesta/pages/IngestaInteligentePage.jsx` | Readiness/ingesta | readiness | Desconectada | FUSIONAR en `/datos/importaciones` como paso/estado |
| Emisiones | `features/emisiones/EmisionesView.jsx` | Vista emisiones legacy | emisiones/RegistroEmision | Desconectada/legacy | RETIRAR; conservar sólo lectura histórica dentro de gobernanza/reportes si se requiere |
| Emisiones stable | `features/emisiones/EmisionesStableView.jsx` | Segunda vista emisiones | emisiones/actions | Duplicada/legacy | ELIMINAR_AL_FINAL después de migrar lectura histórica |
| Detalle etapa | `features/etapas/pages/EtapaObraDetailPage.jsx` | Placeholder | Ninguno | Placeholder/desconectada | ELIMINAR_AL_FINAL; detalle será ruta de estructura si existe necesidad real |
| Detalle organización | `features/organizaciones/pages/OrganizacionDetailPage.jsx` | Placeholder | Ninguno | Placeholder/desconectada | ELIMINAR_AL_FINAL; integrar en administración |
| AserraderoModulePage | `presets/aserradero/pages/AserraderoModulePage.jsx` | Renderer común sectorial | configuración + shared APIs | Funcional interno | MOVER a feature operacional compartida; preset entrega config |

## 5. Navegación actual

```text
pathname /
└─ Landing
pathname /verificar/*
└─ VerificarObra
cualquier otro pathname
└─ Providers → App
   ├─ sin usuario → Login
   ├─ sin organización → Organizaciones
   └─ Navbar + Sidebar desktop/móvil
      └─ preset.navigation → setActiveView(view)
         └─ ActiveView (cadena de if)
```

Navbar y Sidebar reciben callbacks imperativos. El menú móvil replica Sidebar, aunque reutiliza el componente. Los presets deciden una lista plana. No hay rutas protegidas, breadcrumbs, jerarquía de obra ni persistencia de pantalla. `appRoutes` lista sólo diez vistas y no es consumido.

## 6. Arquitectura de información objetivo

La jerarquía propuesta se mantiene cercana al producto real, con Obra como contexto primario sólo cuando corresponde:

```text
Inicio
Obras
└─ Workspace de obra
   ├─ Resumen
   ├─ Operación ambiental
   │  ├─ Transporte y combustible
   │  ├─ Energía y generación
   │  ├─ Agua
   │  ├─ Materiales y residuos
   │  ├─ Ruido
   │  └─ Hídrica/suelo
   ├─ Indicadores
   ├─ Problemas y acciones
   ├─ Evidencia
   ├─ Timeline
   └─ Informes
Datos
├─ Importaciones e ingesta
├─ Evidencias
└─ Revisión/calidad de datos
Operación transversal
├─ Activos
├─ Sensores
└─ Estructura operacional
Inteligencia
├─ Problemáticas y acciones
└─ Copiloto
Gobernanza
├─ Metodologías
├─ Factores
├─ Revisión profesional
└─ Informes regulatorios
Administración
├─ Organización
├─ Usuarios
├─ Diagnóstico y capacidades
└─ Configuración
```

“Operación transversal” conserva activos/sensores que pueden existir antes de seleccionar obra. Dentro del workspace se muestran los mismos features filtrados, no copias.

## 7. Scope de construcción

| Módulo | Estado actual | Destino |
|---|---|---|
| Transporte | Panel Activity Core y tab obra/legacy | `obra/operacion/transporte`, usando transporte V2 |
| Combustible | Observación/flujo y placeholder transporte | `obra/operacion/combustible`, vista configurada sobre Activity Core |
| Energía | `SectorFlowsPanel` organización | `obra/operacion/energia`; generación como sección separada |
| Agua | `SectorFlowsPanel` | `obra/operacion/agua` |
| Materiales | `MaterialsOperationalPanel` | `obra/operacion/materiales` |
| Residuos | flujo sectorial | `obra/operacion/residuos` |
| Generación | flujo sectorial | `obra/operacion/energia/generacion`, sin netear automáticamente |
| Ruido | flujo/puntos ambientales, sin página | `obra/operacion/ruido` como configuración del feature sectorial |
| Hídrica/suelo | flujo/puntos ambientales, sin página | `obra/operacion/hidrica-suelo` |

No se crearán nueve aplicaciones. Serán rutas/configuraciones del workspace que reutilizan Activity Core, flujos y componentes comunes.

## 8. Routing objetivo y ownership

| Ruta | Owner |
|---|---|
| `/`, `/login`, `/verificar/:codigo` | public/auth/obras |
| `/inicio` | `features/inicio` |
| `/obras`, `/obras/:obraId` | `features/obras` |
| `/obras/:obraId/{operacion,indicadores,problemas,evidencias,timeline,informes}` | layout `ObraWorkspace`, feature correspondiente |
| `/obras/:obraId/operacion/:flujo` | `features/operacion` + configuración preset |
| `/datos/{importaciones,evidencias,revision}` | features de datos |
| `/operacion/{activos,sensores,estructura}` | features operacionales transversales |
| `/inteligencia`, `/inteligencia/{acciones,copiloto}` | intelligence/actions/copiloto |
| `/gobernanza/{metodologias,factores,profesional,informes}` | features gobernanza/reportes |
| `/administracion/{organizacion,usuarios,diagnostico,configuracion}` | features administración |

Los IDs de organización provienen de membresía/provider; los IDs de obra provienen de la URL y se validan contra la organización activa. Un cambio de organización redirige a `/inicio` o una obra válida, nunca conserva una obra ajena.

## 9. Arquitectura de carpetas objetivo

```text
src/
  app/
    router/
    providers/
    layouts/
    guards/
  features/
    auth/ inicio/ obras/ operacion/ activos/ sensores/
    datos/ evidencias/ calidad/ indicadores/ problematicas/
    acciones/ copiloto/ metodologias/ factores/ professional/
    reportes/ organizaciones/ usuarios/ diagnostico/ configuracion/
  shared/
    ui/ hooks/ services/ utils/
  presets/
    registry.js
    construccion/ aserradero/ forestal/ transporte/ industrial/
  assets/
  styles/
```

| Carpeta actual | Decisión | Regla |
|---|---|---|
| `app` | KEEP | Bootstrap, router, providers, guards y layouts; sin páginas de dominio |
| `features` | KEEP/autoridad | Una capacidad de producto por feature, con pages/components/hooks/api propios |
| `shared` | KEEP | UI y utilidades sin conocimiento de negocio; cliente HTTP genérico |
| `presets` | KEEP reducido | Datos/config/adapters pequeños; no páginas completas duplicadas |
| `assets`, `styles` | KEEP | Recursos y tokens/globales |
| `core` | MERGE → features/shared | No representa una capa distinta; vaciar durante UX-02–UX-09 |
| `domain` | MOVE | Resolver/matriz sectorial a `presets/shared` o feature correspondiente |
| `layouts` | MOVE → `app/layouts` | Única autoridad de shell/layout |
| `landing` | MOVE o KEEP explícito | Feature público, sin arquitectura paralela |

### Responsabilidad futura

- `app`: composición global, rutas y lifecycle.
- `features`: dominio visible y casos de uso; nunca importa páginas de otro feature para duplicarlas.
- `shared/ui`: componentes presentacionales sin endpoints, organización ni modelos ambientales.
- `shared/services`: Axios, CSRF, errores y descarga genéricos; sin reglas de negocio.
- `presets`: capacidades, etiquetas, navegación adicional y configuración de renderers.
- `styles`: tokens y estilos globales; las excepciones de feature permanecen locales sólo si son genuinas.

## 10. Presets

El registry actual y los módulos `dashboard/evidence/factors/import/intelligence/report` son configuración legítima. Las siete páginas aserradero no deben permanecer como una miniaplicación: seis son wrappers del mismo `AserraderoModulePage`; ese renderer migrará a operación compartida. `LotesForestalesPage` tiene dominio real y migrará a un feature. El preset final registra `capability`, label, icono, orden, renderer/configuración y rutas habilitadas. No importa layouts, providers ni páginas completas.

## 11. Componentes duplicados

| Familia | Variantes actuales | Autoridad futura |
|---|---|---|
| KPI card/grid | `KpiCard`, `EnvironmentalKpiCard/Grid`, `PresetKpiGrid`, `FactorKpiGrid`, `EvidenceKpiGrid`, `ReportKpiGrid`, `ObrasKpis` | `shared/ui/KpiCard` + composición de feature |
| Tabla/paginación | `DataTable`, tablas HTML locales, `EvidenceTable` x2, `ImportPreviewTable` x2, `ReportTable`, `ObrasTable`, `Pagination`, paginación manual | `shared/ui/DataTable/Pagination`; columnas en feature |
| Modal | `Modal`, `AnimatedModalShell`, `ConfirmationModal`, modales environmental y modales inline | `shared/ui/Modal` con variantes confirm/form/drawer |
| Header/hero | `EvidenceHero`, `FactorHero`, `ImportHero`, `ReportHero`, headers de dashboard/obras | `shared/ui/PageHeader`; contenido en feature |
| Badge/status | `Badge`, `EvidenceStatusBadge`, `FactorCategoryBadge`, badges inline | `shared/ui/Badge/StatusBadge` |
| Empty/loading | `EmptyState`, `EvidenceEmptyState`, `ImportEmptyState`, loaders inline, `PlatformLoader` | `shared/ui/EmptyState/Loader` |
| Tabs | `Tabs`, `ObraTabs`, `OrganizacionTabs`, tabs inline | `shared/ui/Tabs`; configuración por workspace |
| Cards/panels | `ChartCard` y decenas de cards con clases repetidas | primitives `Card/Panel`; no abstraer contenido de dominio |
| Forms/filters | filtros factores y formularios por página con inputs repetidos | primitives de UX-03; schemas permanecen por feature |

La consolidación ocurrirá en UX-03 y al migrar cada pantalla; no se hará un reemplazo masivo sin validar comportamiento.

## 12. Estilos

`styles/theme.css` e `index.css` ya aportan variables y base, pero hay 429 coincidencias de patrones visuales repetidos y numerosos radios/sombras arbitrarios (`rounded-[...]`, `shadow-[...]`). También existen colores hexadecimales en mapas/gráficos y estilos especializados. El objetivo de UX-03 será: tokens semánticos de color/spacing/radius/shadow; componentes consumen tokens; dark mode sólo se declara si se soporta integralmente; colores de visualización se centralizan; se eliminan utilities duplicadas al migrar, no mediante reformat global.

## 13. Patrón API objetivo

1. `shared/services/http.js`: única instancia Axios, base URL, CSRF, credenciales, normalización de error, cancelación y descarga.
2. Cada feature expone `api/*.js` con paths tenant-safe y DTO/mappers propios.
3. Las páginas no usan Axios/fetch directamente.
4. `shared/services/api.js` se vacía por extracción progresiva; aliases y stubs se retiran cuando migra su consumidor.
5. Organización se pasa explícitamente al service. Obra se pasa desde params de ruta; ningún service la infiere de UI global.
6. Errores conservan status/código/campos; la UI decide mensaje. No se ocultan como arrays vacíos salvo estados opcionales documentados.
7. Cache: no introducir store global en UX-01. Una futura capa de server-state se evaluará sólo si el patrón de carga lo justifica; no se agrega librería por anticipación.

## 14. Estado y contextos

| Estado | Decisión |
|---|---|
| `AuthContext` | KEEP; sesión/roles y acciones auth |
| `OrganizacionActivaContext` | KEEP; membresías, organización activa y persistencia |
| `FactoresContext` | Revisar en migración de gobernanza; no debe ser provider global si sólo sirve a factores |
| Navegación `activeView` | REMOVE al implementar router |
| Menú móvil | Local en layout global |
| Obra seleccionada | URL como autoridad; loader/context acotado al `ObraWorkspace`, no provider global permanente |
| Formularios, tabs, filtros, modales | Estado local o de ruta/query string según necesidad de persistencia |
| Datos remotos | Hooks por feature; no Context gigante |
| Preset activo | Derivado de organización; registry puro, sin estado paralelo en localStorage |

## 15. Matriz old → new y eliminación

| Old | New único | Fin de migración |
|---|---|---|
| `App.ActiveView` + `activeView` | router declarativo | Eliminar ambos y `appRoutes` incompleto |
| `layouts/*` | `app/layouts/*` | Mover imports; borrar carpeta vieja |
| `core/dashboard` | `features/inicio` | Mover, no copiar |
| `core/copiloto` | `features/copiloto` | Mover |
| `core/{evidencias,importaciones,factores}` + variantes feature | feature existente consolidado | Elegir comportamiento válido, actualizar imports, borrar duplicado |
| `core/reportes*` + `features/reportes` | `features/reportes` | Unificar reportes de obra/regulatorios |
| `core/environmental` | features dueños + `shared/ui` | Distribuir por caso de uso, no crear `environmental-v2` |
| `domain/environmental` | `presets/shared` | Mover resolver/config |
| páginas `presets/aserradero` | renderer de operación + config preset | Borrar wrappers; mover lotes a feature |
| detalle modal obra | rutas hijas `ObraWorkspace` | Borrar modal como navegación principal |
| placeholders transporte | features reales existentes/rutas | Retirar de menú y eliminar placeholder |
| `shared/services/api.js` | HTTP genérico + API por feature | Eliminar funciones al migrar último consumidor |
| componentes duplicados | `shared/ui` | Borrar variante al migrar cada consumidor |
| páginas skeleton desconectadas | destino real o eliminación | No quedan exports sin ruta/test/consumidor |

Elementos previsiblemente eliminados: `ActiveView`, `activeView`, `placeholderViews`, `appRoutes` actual, `core/`, `domain/`, `layouts/`, wrappers sectoriales, páginas `*View` duplicadas, componentes placeholder y estilos obsoletos. Sólo se eliminan en la fase que migra y verifica su último consumidor.

## 16. Estrategia de migración sin dos arquitecturas

Cada fase trabaja por corte vertical:

1. Seleccionar rutas/vistas concretas y declarar cuál archivo actual es autoridad.
2. Mover con historial cuando sea posible; adaptar imports en el mismo cambio.
3. Conectar la ruta definitiva y todos los enlaces/botones.
4. Verificar permisos, organización/obra, carga, error, vacío, móvil y build.
5. Eliminar registro, archivo y estilos reemplazados antes de cerrar la fase.
6. Prohibido crear sufijos `New`, `V2`, `Legacy` o una segunda raíz/router. Si existe un nombre V2 backend, el frontend definitivo usa el nombre de producto.
7. Un adapter temporal sólo puede vivir dentro de la fase y debe desaparecer o quedar documentado como contrato estable al cerrarla.

## 17. Orden UX-02 → UX-10

| Fase | Corte y salida única |
|---|---|
| UX-02 | Router, guards, layouts y navegación base; elimina `activeView`, `appRoutes` parcial y `layouts/` viejo |
| UX-03 | Tokens y primitives UI; consolida componentes al migrar consumidores iniciales |
| UX-04 | Inicio + Obras listado + `ObraWorkspace`/resumen; elimina detalle modal como navegación |
| UX-05 | Operación de obra y flujos construcción; scope obra y presets como configuración |
| UX-06 | Datos: importaciones, evidencias y revisión/calidad; elimina duplicados `core` |
| UX-07 | Indicadores, problemáticas, acciones y timeline dentro/fuera de obra |
| UX-08 | Inteligencia y Copiloto; contexto y comandos con navegación real |
| UX-09 | Gobernanza, profesional, factores/metodologías e informes; consolida reportes |
| UX-10 | Administración, presets restantes, accesibilidad/responsive, limpieza final de carpetas/deuda y regresión UX |

## 18. Reglas de no duplicación

- Una URL tiene una página autoridad.
- Un feature tiene un único directorio autoridad.
- Preset no crea app, layout, provider, cliente HTTP ni copia de feature.
- No se agregan archivos `New`, `V2`, `Stable` o `Legacy` como estrategia de migración.
- Mover implica actualizar imports y borrar origen en la misma fase.
- Un componente entra a `shared/ui` sólo si carece de conocimiento de dominio y tiene al menos dos consumidores reales.
- No se deja navegación visible hacia placeholder.
- Backend y contratos Fase 17 permanecen cerrados; la UI se adapta a ellos.

## 19. Decisión final UX-01

La autoridad futura será `app + features + shared + presets + assets + styles`. La navegación será URL-first, con organización como contexto de sesión y obra como parámetro/contexto del workspace. El frontend actual se migrará por cortes verticales, eliminando cada autoridad antigua en la misma fase. No se crea una segunda aplicación ni se conserva indefinidamente una arquitectura paralela.

## 20. UX-02 — Routing real y App Shell unificado

UX-02 se implementó sobre el commit `1d80635060d0e9c4b2f6dafa72a0a842a5dafb3e`.

### Router y estructura

- Dependencia: `react-router-dom` 7.x, compatible con React 19.
- Bootstrap único: `Root.jsx → BrowserRouter → AppRouter`.
- Autoridad de rutas: `src/app/router/router.jsx`.
- Shell: `src/app/layouts/AuthenticatedLayout.jsx` con Navbar, Sidebar reutilizado en desktop/móvil, breadcrumbs y `Outlet`.
- Workspace: `src/app/layouts/ObraWorkspaceLayout.jsx`; `obraId` proviene exclusivamente de `useParams`.
- Navegación: `src/app/navigation.js`; contiene labels, paths e iconos, pero no componentes.
- Providers existentes se montan una vez mediante un boundary de rutas. Landing y verificación pública quedan fuera del shell.

### Árbol implementado

```text
/
/login
/verificar/:codigo
/inicio
/obras
/obras/:obraId
  /resumen
  /operacion
  /indicadores
  /problemas
  /evidencias
  /timeline
  /informes
/datos/importaciones
/datos/evidencias
/operacion/activos
/operacion/sensores
/inteligencia
/inteligencia/acciones
/inteligencia/copiloto
/gobernanza/factores
/gobernanza/informes
/administracion
/administracion/organizacion
/administracion/usuarios
/administracion/configuracion
/administracion/diagnostico
/administracion/estructura
```

También existen rutas definitivas de extensión aserradero bajo `/operacion`: recepción de trozas, producción, secado, energía, transporte forestal, residuos/subproductos y lotes forestales.

### Guards y comportamiento

- `RequireAuth`: conserva `AuthContext`; redirige a `/login` guardando `returnTo`.
- Login/bootstrap/demo: vuelve a `returnTo` o `/inicio`.
- `RequireOrganization`: conserva `OrganizacionActivaContext`; sin organización redirige a `/administracion/organizacion`, donde se mantiene la creación inicial.
- Cambiar organización desde Sidebar navega a `/inicio`, evitando conservar una obra anterior.
- El workspace recarga la obra con el ID de URL y rechaza/redirecta un owner distinto de la organización activa.
- La ruta pública de verificación usa `useParams`, no inspección manual de pathname.
- Rutas desconocidas muestran 404 público o 404 dentro del shell.
- El historial, refresh y back/forward quedan delegados al router/navegador.

### Migración y eliminaciones

- Eliminados `App.jsx`, `app/routes.jsx` y `layouts/MainLayout.jsx`.
- Movidos Navbar/Sidebar desde `src/layouts` a `src/app/layouts`; la carpeta antigua quedó eliminada.
- Eliminados `activeView`, `ActiveView`, callbacks de cambio de vista, placeholders globales y registro manual de páginas.
- Sidebar usa `NavLink`; Navbar usa `Link/useNavigate`; el drawer móvil reutiliza el mismo Sidebar y cierra al cambiar la ruta.
- Los presets dejaron de emitir `view`; usan `navigationExtensions` con paths. Los placeholders transporte no se exponen.
- `ObrasPage` navega al workspace mediante URL en lugar de abrir el detalle modal como autoridad.
- Breadcrumbs mínimos derivan de segmentos de ruta.

### Validación y pendiente siguiente

- Búsqueda estática: cero ocurrencias de la arquitectura `activeView` y del routing manual anterior.
- ESLint: 0 errores; permanecen 19 warnings preexistentes.
- Build Vite: aprobado.
- Backend: no modificado.
- UX-03 queda pendiente: tokens y primitives visuales. UX-04/UX-05 completarán el contenido definitivo del workspace; UX-02 sólo establece routing y layout base.

## 21. UX-03 — Design System unificado

UX-03 se implementó sobre el commit `9ebfb472a64d352ce193ba48c9b1ee101ab4e312` sin modificar backend ni iniciar el rediseño de Inicio/Obras.

### Identidad y principios

Carbono Zero usa una interfaz técnica, sobria y orientada a datos. El verde identifica marca y acciones primarias; los estados usan color por significado. Principios:

1. claridad sobre decoración;
2. estados explícitos sobre ceros ficticios;
3. una acción primaria por sección;
4. información jerarquizada;
5. color comunica significado;
6. no usar verde para todo;
7. scopes visibles;
8. trazabilidad accesible;
9. responsive desde la primitive;
10. patrones consistentes.

### Tokens

`styles/theme.css` dejó de contener el ejemplo Vite y es la autoridad de tokens. Define:

- fondos `bg-app/surface/surface-subtle/elevated`;
- bordes `default/subtle/strong`;
- texto `primary/secondary/muted/disabled`;
- marca `brand-primary/hover/soft`;
- estados `success/warning/danger/info/neutral`;
- calidad `data-good/review/missing/invalid`;
- sombras `sm/md/lg`, radios `sm/md/lg/xl`;
- layout `content-max/page-padding/section-gap/card-padding`;
- focus ring común.

Light es el tema por defecto y `[data-theme="dark"]` redefine todos los tokens semánticos. Permanecen aliases (`--bg-main`, `--text-main`, `--primary`, etc.) para consumidores aún no migrados; deben desaparecer gradualmente antes de UX-10.

Tipografía: stack actual del sistema, títulos de página 30 px/900, sección 20 px/700, card/body 14–16 px, caption/label 12 px. Iconografía: exclusivamente Lucide, tamaños 16/18/20/24.

### Estructura y primitives definitivas

```text
shared/
  ui/
    Button, IconButton
    Badge, StatusBadge, DataQualityBadge, ScopeBadge
    Card, CardHeader, CardContent, CardFooter
    KpiCard
    PageHeader, SectionHeader
    EmptyState, LoadingState, ErrorState, Alert
    Input, Textarea, Select, SearchInput, FilterBar
    TableShell, TableHead, TableBody, TableCell
    Pagination, Tabs, Modal
    Timeline, TimelineItem
    TraceabilityLink
  charts/
    ChartCard, ChartEmptyState
```

`KpiCard` distingue `null/undefined/""` como “Sin datos”; no transforma ausencia en cero. `Modal` incluye Escape, backdrop configurable, retorno de foco, roles ARIA y adaptación móvil. Tabs son para estado local; navegación usa `NavLink`. Table es una estructura visual pequeña, no un framework. No se creó Drawer porque aún no hay repetición suficiente validada.

Los formatters de `shared/utils/formatters.js` centralizan `formatNumber`, `formatPercent`, `formatCompactNumber`, `formatDate` y `formatDateTime` con locale `es-CL` y ausencia explícita.

### Auditoría y consolidación

| Familia anterior | Decisión UX-03 |
|---|---|
| `Badge`, `KpiCard`, `EmptyState`, `Pagination`, `Tabs`, `ChartCard` en `shared/components` | MERGE: implementación eliminada; alias temporal hacia autoridad `shared/ui`/`shared/charts` |
| `PlatformLoader` | KEEP temporal como loader de bootstrap; loading de sección usa `LoadingState` |
| `Modal`, `AnimatedModalShell`, `ConfirmationModal` | REPLACE progresivo; `shared/ui/Modal` es autoridad para nuevas migraciones, legacy permanece por consumidores no abordados |
| `DataTable` y tablas feature | REPLACE progresivo con primitives Table durante cada corte vertical |
| `Toast` | KEEP: feedback efímero distinto de Alert; migración visual pendiente |
| headers/heroes por core/feature | REPLACE progresivo por PageHeader/SectionHeader |
| cards environmental/domain-specific | KEEP contenido; migrar sólo contenedor visual cuando se rediseñe el feature |

No se eliminaron componentes de dominio. Las implementaciones antiguas fusionadas no constituyen un segundo sistema: sus archivos sólo reexportan la única primitive para evitar una migración masiva de imports en UX-03.

### Consumidores migrados

- Navbar: tokens, `IconButton`, focus y superficies semánticas.
- Drawer móvil del shell: `IconButton` accesible.
- Breadcrumbs: color/focus semánticos.
- Login: `Button` primary/secondary con loading.
- 404: `Card` + `Button`.
- Workspace base: `PageHeader`, `Card`, `CardContent`.
- Consumidores actuales de Badge/KPI/Empty/Pagination/Tabs/Chart reciben la implementación unificada mediante aliases.

### Responsive y accesibilidad

Las primitives usan flex/grid responsivo, overflow horizontal en tablas, ancho/max-height móvil en modal y actions que envuelven. Button/inputs/tabs/links tienen focus visible; disabled y loading son explícitos; IconButton exige `aria-label`; Modal usa `role=dialog`, `aria-modal`, Escape y restaura foco. La auditoría WCAG completa queda para UX-10.

### Pendientes UX-04+

- Migrar cards, headers y tablas internas al rediseñar cada página.
- Sustituir modales legacy por el Modal definitivo y eliminar `AnimatedModalShell` cuando quede sin consumidores.
- Migrar Toast y PlatformLoader a tokens sin alterar su semántica.
- Retirar reglas globales invasivas y aliases CSS antes de UX-10.
- No se creó ruta/showcase ni otro design system.

## UX-04 — Inicio, Obras y workspace central

`/inicio` es ahora el centro de control ambiental de la organización activa. Sus KPIs, obras, pendientes y actividad reciente se construyen sólo desde obras, problemáticas, evidencias y contextos reales. La ausencia de información se presenta como “Sin datos” o mediante estados vacíos; no se generan ceros ni alertas ficticias.

`/obras` usa cards accesibles, filtros por búsqueda, estado operacional, estado ambiental y perfil, y mantiene la creación con el contrato existente. La obra creada abre su URL autoritativa. El detalle modal, la tabla/dashboard anteriores y `core/dashboard` fueron eliminados al quedar sin consumidores.

El workspace `/obras/:obraId/*` carga obra, contexto, indicadores y timeline una vez y los comparte mediante `Outlet`. Su header comunica obra, organización, perfil, estado y fechas; la navegación horizontal continúa gobernada por URL. Un recurso ausente o fuera del tenant produce el mismo mensaje “No se encontró la obra”.

El resumen conecta estado y diagnóstico ambiental, aplicabilidad de capacidades a nivel obra, indicadores destacados, problemas, acciones, evidencia, timeline y cierre. Las capacidades de la organización permanecen separadas de la aplicabilidad de la obra.

Servicios creados: `features/inicio/services/inicioApi.js` y `features/obras/services/workspaceApi.js`. Usan `/organizaciones/:id/obras/`, `/problematicas/`, `/evidencias/` y, por obra, `/contexto/`, `/timeline/` e `/indicadores/`. No se modificó backend ni se reprodujo lógica metodológica en frontend.

Las rutas profundas conservan contexto y navegación coherentes; salvo Operación existente, permanecen explícitamente como bases temporales. Los dashboards sectoriales profundos quedan para UX-05 y el workflow documental para UX-06.

Correctivo semántico final: los conteos exitosos preservan `0` como dato real y reservan “Sin datos” para `null`/`undefined`; el KPI de Inicio se denomina “Obras registradas” porque cuenta el listado completo sin inventar una definición de obra activa. Los indicadores destacados usan selección explícita: agregados nombrados de transporte y totales aditivos tipados de flujos, con su unidad real. IDs, alcance, estrategia de agregación, flags, códigos, estados internos y metadata nunca se convierten automáticamente en KPIs.

## UX-08 — Inteligencia, Copiloto, activos y sensores

`/inteligencia` contiene exclusivamente resultados operacionales reales: prioridades, recomendaciones determinísticas y escenarios provistos por backend. Cada recurso falla de forma independiente y una respuesta vacía produce `EmptyState`; se eliminaron `fallbackCards`, `ensureThreeCards` y la exigencia visual de tres recomendaciones. Revisión profesional y conocimiento se retiraron de esta ruta y permanecen pendientes para UX-09.

`/inteligencia/copiloto` consume Context Gateway, propuestas, feedback y comandos reales sobre una problemática seleccionada. Presenta contexto estructurado, referencias, restricciones y versiones sin exponer prompts ni razonamiento interno. Aceptar sólo prepara un comando y requiere una segunda confirmación humana antes de crear la acción formal en UX-07. Un fallo del proveedor queda aislado del resto del producto.

`/operacion/activos` usa primitives UX-03, filtros, CRUD en modal, condición reciente, mantenimiento real y enlaces a sensores. No convierte condición operacional en impacto ambiental. `/operacion/sensores` y `/operacion/sensores/:sensorId` separan dispositivo, activo e instalación; muestran calibraciones, lecturas y calidad técnica. La carga manual está identificada y una lectura enlazada abre la trazabilidad UX-06. No existe cálculo de CO₂e en estas vistas.

Se retiraron el shell futuro de Copiloto, `IntelligencePanel`, su tablero legacy de acciones y las listas visuales core reemplazadas. Se conservaron los servicios de acciones legacy que aún alimentan reportes fuera del alcance UX-08. No se agregaron librerías ni se modificó backend.

Limitaciones: el contrato de sensor entrega las últimas veinte lecturas embebidas, sin paginación para una serie histórica extensa; UX-08 no inventa esa capacidad. Los endpoints actuales permiten crear activos y sensores, pero no exponen eliminación en esta experiencia.

## UX-07 — Problemas, acciones y mejora verificable

`features/mejora` es la única autoridad frontend para el ciclo Problema → Alcance → Indicadores → Acción → BASE → Implementación → Seguimiento → RESULT → Decisión → Historial. Las rutas organizacionales son `/inteligencia/problemas` y `/inteligencia/problemas/:problemId`; las rutas obra-scoped son `/obras/:obraId/problemas` y `/obras/:obraId/problemas/:problemId`. La URL, no un selector local, determina el problema activo.

La vista de obra envía `?obra=<id>` en listado, detalle y cada recurso hijo, usando el correctivo backend PRE-UX-07. Cada recurso carga de forma independiente: una falla de historial no oculta acciones, indicadores o BASE. Un `404` específico de snapshot se representa como “BASE pendiente”; otros fallos permanecen errores.

La experiencia distingue acción propuesta, seleccionada, iniciada, implementada, medición y resultado evaluado. Iniciar requiere confirmación mediante `Modal` y comunica el congelamiento de BASE. Las mediciones manuales se identifican como declaradas y el motor se presenta como datos actuales, nunca como IA. BASE y RESULT preservan ceros mediante semántica nullish; las comparaciones usan exclusivamente métricas entregadas por backend y no infieren dirección de mejora.

Los ciclos y el historial permanecen inmutables y visibles. Reevaluación y escalamiento usan sus endpoints gobernados y nunca `PATCH` directo. La evidencia reutiliza `TraceabilityLink` y `TraceabilityDrawer` de UX-06 cuando el seguimiento expone una referencia. Se retiraron `ProblemWorkspaceV2`, `problematicasV2Api` y la aplicación legacy de acciones; `/inteligencia/acciones` redirige a la vista unificada.

Copiloto, propuestas y feedback IA no forman parte del nuevo detalle. Permanecen en sus rutas existentes para UX-08. La gobernanza metodológica y profesional tampoco fue modificada.

## UX-06 — Datos, evidencias, importaciones y trazabilidad

`features/datos` es la única autoridad frontend para alimentación y procedencia de datos. Sus rutas son `/datos`, `/datos/evidencias`, `/datos/evidencias/:evidenceId`, `/datos/importaciones`, `/datos/importaciones/:processId` y la vista reutilizada `/obras/:obraId/evidencias`. Se retiraron las páginas, aliases, componentes y servicios duplicados anteriores.

El centro Datos combina evidencias e importaciones con tolerancia a fallos parciales. Evidencia lista metadata, carga el archivo original sin fingir extracción automática y obtiene versiones desde ContextGateway. La ruta de obra consume exclusivamente el endpoint obra-scoped. Importaciones representa origen → archivo → contexto → mapping → preview → revisión por excepción → confirmación → resultado; sólo promete CSV/XLS/XLSX para procesamiento tabular.

El `Drawer` compartido aporta Escape, restauración de foco, overlay y comportamiento responsive. `TraceabilityDrawer` separa valor/calidad, fuente de datos, evidencia, versión concreta e ingesta. `TraceabilityLink` abre el panel desde los dominios UX-05.

Limitación: no todas las vistas entregan un grafo unificado de cálculo histórico hasta metodología/factor. UX-06 no reconstruye ese tramo con recursos activos ni lo inventa. El ciclo Problema → BASE → Acción → RESULT permanece para UX-07.

## UX-05 — Operación ambiental de obra

`/obras/:obraId/operacion` es el resumen operacional obra-scoped y contiene navegación URL hacia Energía, Agua, Combustibles, Transporte, Materiales, Residuos, Ruido e Hídrica/suelo. Energía integra generación propia. Cada dominio distingue aplicabilidad (`No aplica`, `Por definir`), ausencia, datos disponibles y revisión requerida.

La carga común usa exclusivamente contratos backend acotados por obra: viajes e indicadores `?obra=`, puntos `?obra=`, registros sectoriales `?obra=`, eventos de materiales `?obra=`, balances materiales por obra y `work_indicators`. No se filtran viajes en frontend ni se consumen agregados organizacionales para representar la obra.

Los selectors son explícitos. Sólo `estrategia_agregacion=suma` permite mostrar total; series no aditivas muestran cantidad y rango. Ruido nunca suma dB. Los registros ambiguos muestran “Requiere revisión”. Transporte utiliza nombres y unidades cerradas del contrato (`viajes`, `km`, `t`, `t·km`, `L`, `%`). Materiales usa el balance determinístico y no trata `cantidad_inicial` como autoridad. Residuos sectoriales y residuos originados en eventos materiales permanecen en secciones separadas para evitar doble conteo.

Los registros presentan fecha, concepto, valor, unidad, contexto, calidad y enlace al origen cuando existe. Los CTA sin datos dirigen a Evidencia o Importaciones; el workflow documental completo continúa pendiente para UX-06. Se eliminó `OperacionPage` organizacional legacy junto con sus paneles stateful de Activity Core, transporte, materiales y flujos. Las rutas específicas de aserradero permanecen intactas.

Correctivo final UX-05: la operación usa carga parcial por recurso. Cada request conserva un estado discriminado `ready/error` y `data`; un error de endpoint nunca se transforma en una colección vacía. Transporte aísla viajes de indicadores, Materiales aísla balance de eventos, Residuos conserva sus dos fuentes separadas y los dominios sectoriales continúan mostrando registros cuando sólo fallan los puntos ambientales. El overview representa una falla como “No disponible”, distinta de “Sin datos”.
