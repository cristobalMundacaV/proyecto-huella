# Carbono Zero — Product Experience V1

## PX-01 — Navegación por preset

El sidebar responde a la pregunta “¿a dónde voy para hacer mi trabajo?” y deja de representar el sitemap técnico. Existe una sola autoridad en `app/navigation.js`, compuesta por capacidades base con identificadores estables y perfiles declarativos incluidos en cada preset.

### Capacidades y composición

Las capacidades reutilizables incluyen Inicio, unidad operacional, Activos, Sensores, Evidencias, Importaciones, Inteligencia, Problemas y acciones, Copiloto, Gobernanza, Revisión profesional y Administración. Cada preset compone cinco grupos: Mi operación, Datos, Gestión ambiental, Control y Configuración. Las rutas profundas de Gobernanza y Administración permanecen disponibles mediante sus respectivas páginas y breadcrumbs, sin saturar la navegación principal.

### Experiencias sectoriales

- Construcción presenta Obras, Activos y Sensores como operación; prioriza Evidencias antes de Importaciones.
- Aserradero presenta Plantas y agrupa Recepción, Producción, Secado, Energía, Transporte forestal, Residuos y Lotes dentro de “Procesos de planta”.
- Forestal reutiliza la composición sectorial con el título “Procesos forestales”.
- Industrial usa Líneas como unidad operacional.
- Transporte usa Rutas como unidad operacional.
- Un preset desconocido conserva el fallback Construcción.

### Sidebar y contexto

El bloque “Estado de la empresa” fue retirado. La organización activa aparece como contexto compacto en la parte superior, acompañada por el rubro sin exponer la palabra interna “preset”. Cambiar organización recompone inmediatamente la navegación y vuelve a Inicio, evitando conservar una ruta sectorial incompatible. Desktop y drawer móvil consumen exactamente la misma navegación; el drawer se cierra después de navegar.

La navegación de obra permanece gobernada exclusivamente por `ObraWorkspaceLayout`. No se duplican Resumen, Operación, Indicadores, Problemas, Evidencias ni Historial en el sidebar global.

### Progressive disclosure y accesibilidad

Gobernanza abre la superficie que contiene revisión, expedientes, calidad, factores, auditoría e informes. Administración abre organización, usuarios, configuración, diagnóstico y estructura. La subnavegación sectorial usa botón real con `aria-expanded`; el nav tiene nombre accesible, los iconos son decorativos y el selector de organización posee label.

Pendiente para PX-02: rediseño visible del contenido de Inicio. PX-01 no modifica páginas funcionales ni contratos backend.

## PX-02 — Inicio ejecutivo

Inicio responde “¿qué necesita mi atención ahora y dónde debo entrar?”. La pantalla se limita a contexto humano, tres KPIs de priorización, hasta cinco pendientes, un máximo de cuatro unidades operacionales y hasta tres eventos recientes cuando existen. No contiene gráficos, escenarios, recomendaciones extensas ni accesos rápidos redundantes.

Las prioridades se ordenan sin score: primero unidades con estado `requiere_atencion` o `cierre_pendiente`, luego problemas abiertos y finalmente evidencias documentales pendientes. Si una unidad ya representa la atención, sus problemas no se repiten en la lista principal. Los enlaces de problema usan la ruta scoped cuando el payload entrega obra; nunca se infiere una asociación.

Las unidades usan una tarjeta compacta feature-local con estado, principal señal disponible y enlace semántico. Se muestran primero las que requieren atención. Una sola unidad no fuerza una grilla sobredimensionada; diez unidades se resumen en cuatro y mantienen “Ver todas”. El vocabulario usa `unitLabel` y `unitPluralLabel`: Obras, Plantas, Líneas o Rutas según la organización.

Sin unidades, Inicio se transforma en onboarding y no muestra paneles de ceros. Sin pendientes, presenta “Todo al día”. Problemas y evidencias cargan de forma independiente; su error se representa como “No disponible” sin ocultar las unidades. Obras es el recurso esencial. Una identidad de request evita que una respuesta tardía de la organización anterior reemplace la actual.

Los fallos de contexto se conservan por ID de unidad: estado no disponible no se presenta como estado saludable. `estado_ambiental` incluido en la unidad es el único fallback autoritativo; sin ese campo, el KPI, la lista de atención y la tarjeta compacta comunican que la verificación está incompleta.

Pendiente para PX-03: renovación visible del listado y creación de unidades operacionales. PX-02 no modifica `/obras`, sus contratos ni el backend.
