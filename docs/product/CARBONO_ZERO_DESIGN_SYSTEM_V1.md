# CARBONO ZERO — DESIGN SYSTEM V1

## Principios

- **Extraer y consolidar, no rediseñar.** Este documento formaliza patrones visuales que ya existían en el dashboard de obra, el dashboard de portafolio y el sidebar. Ninguna superficie migrada cambia perceptiblemente.
- **Una sola fuente de verdad visual.** Toda pantalla nueva debe construirse combinando los tokens y componentes de este documento antes de inventar valores nuevos.
- **Reutilizar antes de duplicar.** Varias piezas (badges, botones, charts, estados vacíos/error) ya estaban consolidadas en `shared/ui` y `shared/charts`; este trabajo las declara canónicas en vez de reemplazarlas por una nueva librería paralela.

## Tokens

Definidos en [`frontend/src/styles/theme.css`](../../frontend/src/styles/theme.css) bajo `:root`.

### Spacing

Escala de 4 en 4 (rem equivalentes): `--space-1` (4px) · `--space-2` (8px) · `--space-3` (12px) · `--space-4` (16px) · `--space-5` (20px) · `--space-6` (24px) · `--space-8` (32px) · `--space-10` (40px) · `--space-12` (48px).

### Radii

- `--radius-control` — controles pequeños (inputs, chips).
- `--radius-card` — tarjetas de métrica, insight, flujo (18px).
- `--radius-panel` — secciones/paneles de contenido (22px).
- `--radius-hero` — hero ejecutivo (28px).
- `--radius-pill` — badges y barras de progreso (999px).

`--radius-lg`/`--radius-md` (preexistentes) se mantienen para `Card`, `Button`, `Modal`, etc. — no se reemplazaron porque ya eran consistentes.

### Shadows

Máximo 3 niveles nuevos, para no competir con los ya usados por `Card`/`Button`:

- `--shadow-flat` — sin sombra.
- `--shadow-card-v1` — tarjetas de métrica/insight/flujo.
- `--shadow-floating` — hero ejecutivo.

### Motion

- `--motion-fast` (150ms) — hover de tarjetas, transiciones de progreso.
- `--motion-standard` (220ms) — la mayoría de las transiciones de color/fondo.
- `--motion-drawer` (320ms) — drawers/modales.

### Typography

`--type-display` · `--type-h1` · `--type-h2` · `--type-h3` · `--type-body` · `--type-small` · `--type-eyebrow` — escalas de referencia disponibles como variables `font` shorthand. La mayoría de las superficies siguen usando utilidades Tailwind (`text-3xl font-black`, etc.); estos tokens documentan la intención cuando se necesite un valor `font` inline o en CSS.

### Flow colors

Un color por flujo ambiental, ya usado (indirectamente, vía `environmentalDomains.js`) por sidebar, `CZFlowCard` y los charts:

| Flujo | Token | Color |
|---|---|---|
| Energía | `--flow-energy` | ámbar `#a16207` |
| Agua | `--flow-water` | azul `#1d4ed8` |
| Combustibles | `--flow-fuel` | naranja/rojo `#c2410c` |
| Transporte | `--flow-transport` | índigo `#4338ca` |
| Materiales | `--flow-materials` | grafito `#57534e` |
| Residuos | `--flow-waste` | verde `#047857` |
| Ruido | `--flow-noise` | violeta `#6d28d9` |
| Emisiones atmosféricas | `--flow-air-emissions` | celeste `#0369a1` |

La fuente operativa de verdad para color/ícono por flujo sigue siendo [`shared/config/environmentalDomains.js`](../../frontend/src/shared/config/environmentalDomains.js) (`getEnvironmentalDomain`/`getFlowChartColor`), que ya soporta alias de clave. Los tokens `--flow-*` documentan la paleta; el mapeo clave→color/ícono en componentes se sigue resolviendo ahí, no se duplicó.

## Componentes base

Ubicados en [`frontend/src/shared/ui/CarbonoZeroSystem.jsx`](../../frontend/src/shared/ui/CarbonoZeroSystem.jsx), exportados desde `@/shared/ui`.

- **`CZPageHero`** — contenedor del hero ejecutivo (gradiente verde, `--radius-hero`, `--shadow-floating`). Usado en el dashboard de obra y el dashboard de portafolio; el contenido interno (título, pills, panel lateral) sigue siendo específico de cada pantalla vía `children`.
- **`CZMetricCard`** — tarjeta de KPI: `icon`, `label`, `value`, `unit`, `supportingText`/`helper`, `tone` (`neutral|info|success|warning|danger|blue|rose|emerald|amber|violet|orange`), `progress` opcional, `delta` opcional. Reemplaza los `ExecutiveKpi`/`PortfolioKpi` locales que existían duplicados en obra y portafolio.
- **`CZInsightCard`** — tarjeta de insight IA: `priority` (`alta|media|baja`), `title`, `description`, `icon` opcional, `cta` opcional. Reemplaza el markup de insight que estaba inline en `InicioPage`.
- **`CZFlowCard`** — tarjeta de flujo ambiental (usa `getEnvironmentalDomain` para color/ícono/etiqueta).
- **`CZAlertBanner`** — banner de aviso con ícono + texto + acción opcional (`tone`: `warning|info|danger`). Reemplaza los banners de "configuración incompleta" / "métricas no disponibles" que estaban duplicados con markup propio.
- **`CZSection`** — contenedor de sección genérico con `--radius-panel`.
- **`CZProgress`** — barra de progreso de una línea, usada dentro de `CZMetricCard`.
- **`CZStatusBadge`** — alias de `StatusBadge` (ver Badges).

### Ya consolidados (se reutilizan tal cual, sin renombrar)

No fue necesario envolver estos en un alias `CZ*`: ya son la única implementación en la app y ya usan tokens.

- **Botones** — [`Button`/`ButtonLink`/`IconButton`](../../frontend/src/shared/ui/Button.jsx): variantes `primary|secondary|ghost|danger`, tamaños `sm|md`, usa `--radius-md`/`--brand-primary`/`--focus-ring`.
- **Badges** — [`Badge`/`StatusBadge`/`DataQualityBadge`/`ScopeBadge`](../../frontend/src/shared/ui/Badge.jsx): `StatusBadge` ya infiere el tono semántico (`success|warning|danger|info|neutral`) desde el texto del estado — no crear badges de color manual nuevos.
- **Estados universales** — [`EmptyState`/`LoadingState`/`ErrorState`/`Alert`](../../frontend/src/shared/ui/Feedback.jsx).
- **Cards genéricas** — [`Card`/`CardHeader`/`CardContent`/`CardFooter`](../../frontend/src/shared/ui/Card.jsx).
- **Headers** — [`PageHeader`/`SectionHeader`](../../frontend/src/shared/ui/Headers.jsx).

## Charts

Base: **Recharts**, envuelto en [`frontend/src/shared/charts/`](../../frontend/src/shared/charts/):

- `ChartCard` — envoltorio compartido (título, descripción, `loading`, `empty`, `action`) sobre `Card`+`SectionHeader`; ya centraliza el empty state (`ChartEmptyState`) y el loading state de todos los charts.
- `EnvironmentalDonutChart` / `DonutLegend`, `EnvironmentalPieChart`, `EnvironmentalBarChart`, `EnvironmentalTrendChart`, `CoverageProgressChart` — wrappers existentes con tipografía, tooltip, leyenda y colores ya unificados.

No se creó una nueva capa de chart: la existente ya cumple los requisitos (tipografía/tooltip/empty state/leyenda/padding/colores compartidos vía `ChartCard`).

## Métricas — `CZMetricCard`

```jsx
<CZMetricCard
  icon={Leaf}
  label="Huella total"
  value={kpis.huella_total_tco2e}
  unit="tCO2e"
  tone="blue"
  progress={70}          // opcional
  delta="+3% vs. período anterior"  // opcional
  supportingText="Dato del período actual"
/>
```

Tonos: `neutral · info · success · warning · danger` (semánticos) + `blue · rose · emerald · amber · violet · orange` (usados históricamente por los dashboards ejecutivos, mantenidos para no romper la lectura de color que el equipo ya usa por Alcance 1/2/3, riesgo, etc.).

## Insights IA — `CZInsightCard`

```jsx
<CZInsightCard priority="alta" title={insight.title} description={insight.description} />
```

Regla de producto (sin cambios): **máximo 3 insights visibles en superficies ejecutivas** — ya aplicada en `buildPriorities`/`portfolio.insights` upstream, `CZInsightCard` solo formatea, no decide cuántos mostrar.

## Flow Card — `CZFlowCard`

```jsx
<CZFlowCard flow="energia" value={120} unit="kWh" href="/obras/1/operacion/energia" />
```

El color/ícono se resuelve por `flow` vía `getEnvironmentalDomain`; nunca se fija un color a mano.

## Badges

Un solo componente (`StatusBadge`) para todo estado textual (`En ejecución`, `Período incompleto`, `Con datos`, `Sin datos`, `Alta`, `Crítica`, `Pendiente`, `Validado`, etc.) — el tono se infiere del texto normalizado. No crear una clase CSS de badge nueva por pantalla.

## Loading / Empty / Error / Data

- **Loading de contenido** (no arranque de app): `ContextContentSkeleton` (`shared/components`).
- **Loading inline**: `LoadingState`.
- **Empty state**: `EmptyState` (ícono, título, descripción, acciones, `guidance`, `suggestions`).
- **Error state**: `ErrorState` (con `onRetry` opcional).
- **Aviso/alerta con acción**: `CZAlertBanner` (nuevo — antes cada banner tenía su propio markup).

## Densidades

- **Executive** (dashboard de obra, dashboard de portafolio): más aire, KPIs, charts, síntesis — `--space-5`/`--space-6`, `CZPageHero`, `CZMetricCard`, `ChartCard`.
- **Operational** (formularios, tablas de registro, flujos de captura): más compacto — `Table`, `FormControls`, `Card`+`CardContent` con `--card-padding` reducido. No se tocó en esta fase; queda listada para la siguiente migración (Reportes/Control/Configuración/flujos).

## Reglas de uso

1. Antes de escribir un color, radio, sombra o spacing nuevo: revisar si existe un token equivalente en `theme.css`.
2. Antes de crear una tarjeta/badge/loader nuevo: revisar `CarbonoZeroSystem.jsx` y `shared/ui`/`shared/charts`.
3. Los colores de flujo siempre se resuelven vía `getEnvironmentalDomain`/`getFlowChartColor`, nunca hardcodeados por pantalla.
4. Máximo 3 insights IA visibles en cualquier superficie ejecutiva.
5. No introducir una librería de charts distinta a Recharts/`shared/charts`.

## Anti-patterns

No:
- Colores inline arbitrarios (`bg-[#123456]`) cuando existe un token o un tono semántico.
- Márgenes/gaps arbitrarios fuera de la escala de `--space-*` en superficies nuevas.
- Cards nuevas para un patrón que `CZMetricCard`/`CZInsightCard`/`CZFlowCard`/`Card` ya cubren.
- Badges duplicados con CSS propio para el mismo concepto — usar `StatusBadge`.
- Loaders/spinners por pantalla — usar `LoadingState`/`ContextContentSkeleton`.
- Estilos de Recharts por módulo — todo pasa por `shared/charts`.
- Nueva escala tipográfica local — usar las clases Tailwind ya en uso o `--type-*`.
- Sombras/radios arbitrarios (`shadow-[...]`, `rounded-[Npx]`) cuando el valor coincide con un token existente.

## Migración inicial (esta fase)

- **Dashboard de obra** (`ObraResumenPage.jsx` / `WorkExecutiveDashboard`) — hero → `CZPageHero`; KPIs (`ExecutiveKpi` local) → `CZMetricCard`. Charts, `FlowStatusGrid`, `AiRecommendationsPanel` sin cambios.
- **Dashboard de portafolio** (`InicioPage.jsx`) — hero → `CZPageHero`; KPIs (`PortfolioKpi` local) → `CZMetricCard`; insights inline → `CZInsightCard`; banners de aviso (configuración incompleta, métricas no disponibles) → `CZAlertBanner`. Charts y listas (`AttentionList`, obras prioritarias) sin cambios.
- **Sidebar** (`Sidebar.jsx`) — auditado, no modificado en esta fase: ya usa `--focus-ring`/`--sidebar-*`/`--radius-md` donde corresponde; el resto de sus valores (anchos de colapso, sombra ambiental del panel) son específicos de layout, no de un token genérico del design system, y el archivo tenía cambios de una funcionalidad en curso (colapso persistente) no relacionados con esta fase — se dejó intacto para no mezclar ambos cambios en un mismo commit.

### Pendientes (siguientes fases)

- Migrar Reportes, Control, Configuración y las páginas de flujo (`OperacionOverviewPage`, `SectorDomainPage`, etc.) a `CZMetricCard`/`CZSection` donde tengan el mismo patrón.
- Evaluar si el hero de `CZPageHero` necesita una variante sin panel lateral para páginas que no son dashboard ejecutivo.
- Revisar si el sidebar debe adoptar `--radius-card`/`--shadow-card-v1` en su próxima iteración (fuera de esta fase, para no mezclarlo con el trabajo de colapso ya en curso).
