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

## PX-03 — Obras y workspace

### Preguntas de producto

El listado de unidades responde “¿qué unidades tengo y cuál necesita atención?”. El workspace responde “¿qué está pasando en esta unidad y dónde entro para gestionarlo?”. Ninguna de las dos superficies intenta convertirse en un dashboard analítico completo.

### Listado, orden y filtros

El listado prioriza `requiere_atencion`, luego `cierre_pendiente`, después el resto de estados conocidos y finalmente los estados ambientales desconocidos o no disponibles. No existe un score sintético. La búsqueda es el único filtro permanentemente visible: los estados operacional y ambiental provienen de dimensiones distintas y no se fusionan en un estado cliente sin un contrato determinístico que lo respalde.

Cada tarjeta muestra nombre, código, estado ambiental, una única siñal de gestión y ubicación sólo cuando aporta contexto. La resolución del estado prioriza el contexto exitoso y luego `work.estado_ambiental`; un fallo del contexto secundario no invalida un estado ambiental autoritativo ya presente en la unidad. Si el contexto falla, la señal de seguimiento se muestra por separado como “Seguimiento no disponible”; sólo cuando tampoco existe estado en la unidad se presenta “Estado no disponible”. El acceso sigue siendo un enlace semántico y el listado no limita la cantidad de unidades.

### Creación progresiva

El contrato de Obra exige nombre y fecha de inicio; el código puede generarse automáticamente y superficie, ubicación y tipo tienen defaults u opcionalidad en backend. Por eso la primera vista del formulario solicita únicamente lo necesario para comenzar y desplaza datos secundarios a un bloque de detalles. En Construcción, `superficie_m2` se presenta al cliente como “Superficie” con unidad m². Los campos específicos de Construcción no se exponen como si fueran universales para Plantas, Líneas o Rutas.

Después de crear, se conserva la navegación directa al resumen de la nueva unidad.

### Workspace y vocabulario por preset

El header elimina “Workspace de obra” y presenta nombre, código, ubicación opcional y estado. La metadata secundaria se limita a estado operacional, inicio y perfil. El enlace de retorno y los CTA consumen `unitLabel` / `unitPluralLabel`, por lo que Construcción muestra Obras, Aserradero Plantas, Industrial Líneas y Transporte Rutas sin cambiar las rutas React ni duplicar aplicación.

La navegación interna mantiene las seis rutas existentes, pero usa copy de cliente: Resumen, Operación, Indicadores, Problemas, Evidencias e Historial. `/timeline` permanece como ruta interna. El `Outlet` sigue siendo la autoridad de contexto del workspace.

### Resumen de unidad

El resumen jerarquiza primero el estado general y su explicación determinística. Después muestra tres KPIs compactos: problemas abiertos, acciones en curso y evidencias. Los problemas se limitan a tres y son la prioridad operativa; las acciones no duplican una lista completa. Los indicadores destacados se limitan a tres siñales obtenidas del contrato existente, sin ranking arbitrario ni mezcla de unidades. La cobertura ambiental queda como contexto secundario y la actividad reciente se limita a tres eventos con acceso a Historial.

El conteo de evidencias respeta `0` como cero real y `null`/ausencia como “Sin datos”. No se duplica el mismo conteo en otra tarjeta de evidencia.

### Fallos parciales y estado desconocido

La carga del listado conserva explícitamente los IDs cuyos contextos fallaron y usa una identidad de request para impedir que una respuesta tardía de otra organización sobrescriba el estado actual. La lista de unidades es esencial; el contexto individual es secundario.

Un fallo del contexto secundario no invalida un estado ambiental autoritativo ya presente en la unidad. Por eso una unidad puede conservar, por ejemplo, estado `estable` o `requiere_atencion` mientras comunica de forma independiente que su seguimiento no está disponible. Sólo la ausencia simultánea de estado en contexto y en la unidad convierte el estado ambiental en desconocido/no disponible.

En el workspace, contexto, historial e indicadores se separan: el contexto sigue siendo esencial para gobernar la unidad, mientras que Historial e Indicadores pueden fallar de forma aislada y mostrar “No disponible” en su superficie. Un error secundario no convierte el estado ambiental en sano ni derriba el resto del workspace.

### Integración visual, responsive y accesibilidad

Las páginas internas de Problemas, Evidencias, Indicadores e Historial ya no repiten un segundo header de workspace; conservan su funcionalidad y sólo ajustan integración y copy. La navegación horizontal mantiene overflow local en pantallas estrechas; cards y acciones hacen wrap y no se introduce scroll horizontal del body. Se reutilizan primitives existentes, links/botones semánticos, labels y estados textuales. Los fondos de controles usan tokens para conservar dark mode.

### Decisiones pospuestas

PX-03 no rediseña profundamente Operación, Indicadores, Problemas, Evidencias ni Historial. Sus experiencias internas permanecen para fases posteriores de Product Experience. Tampoco inicia PX-04 ni PX-05 y no modifica backend.
