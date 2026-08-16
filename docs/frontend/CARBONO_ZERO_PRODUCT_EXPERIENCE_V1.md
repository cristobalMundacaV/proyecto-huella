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

## PX-04 — Datos, evidencias e importaciones

### Pregunta central y flujo mental

Datos responde “¿qué información tengo, qué falta y qué debo hacer con ella?”. La experiencia visible prioriza el flujo Subir → Entender → Revisar → Confirmar → Resultado. Los nombres internos de ingesta, mapeo y payload permanecen fuera del copy principal cuando existe una expresión de cliente equivalente.

### Evidencia e importación siguen siendo entidades distintas

SOURCE != EVIDENCE se mantiene. Una fuente de datos describe el origen operacional de la información; una evidencia representa un documento o archivo de respaldo y puede tener versiones. Una importación puede referenciar explícitamente una versión de evidencia, pero la interfaz no fusiona ambas entidades ni usa la confiabilidad de una fuente como calidad del documento.

### /datos y prioridades

`/datos` deja de ser un hub de navegación y presenta sólo tres bloques: Requiere atención, Evidencias e Importaciones recientes. Evidencias e importaciones cargan de manera independiente y conservan protección frente a respuestas tardías al cambiar de organización. Un error de un recurso se representa como No disponible sin convertirlo en cero ni ocultar el otro.

Las prioridades no usan score. Para evidencias sólo `pendiente` y `observada` se presentan automáticamente como revisión pendiente. Para importaciones se elevan estados cuyo contrato expresa acción o fallo: `requiere_mapeo`, `listo_para_confirmar`, `fallido` y `completado_con_observaciones`. Estados automáticos como `recibido`, `analizando` y `procesando` se muestran neutrales y no se convierten en falsos pendientes humanos.

### Evidencias y carga documental

La lista de evidencias conserva búsqueda y un único filtro visible por estado. Los estados internos se traducen a copy humano: Pendiente de revisión, Validada, Requiere revisión, Rechazada, Vinculada y Sin vincular. Cada fila se limita a documento, contexto, estado, fecha de ingreso y acción.

Agregar documento mantiene el contrato existente: el frontend envía el archivo con tipo `otro` y estado inicial `pendiente`, sin presentar esos defaults como clasificación automática. La variante organizacional no inventa obra; la variante del workspace usa el endpoint scoped existente y no vuelve a pedir unidad. Carga, error y éxito tienen feedback local independiente; el error de upload no reemplaza la lista. El EmptyState usa un `ref` React para abrir el selector de archivo y elimina `document.querySelector`.

### Detalle de evidencia, versiones y trazabilidad

El detalle responde “¿qué es este documento y qué información produjo?” mediante Documento, Contexto, Versiones y Trazabilidad. El header se limita a nombre, estado, contexto y fecha. El archivo original sólo ofrece acceso cuando `archivo_url` existe en el contrato. Las versiones muestran número, fecha y nombre; checksum queda bajo progressive disclosure en “Detalles de trazabilidad”.

El contrato `/context/evidence/:id` no entrega observaciones individuales, por lo que la interfaz no las reconstruye ni inventa. Cuando la lista de importaciones entrega una relación explícita mediante `version_evidencia_detalle.evidencia`, el detalle ofrece “Ver importación”.

### Import workflow y estados

La nueva importación mantiene soporte tabular auditado para CSV, XLS y XLSX. El stepper visible usa cinco pasos de cliente: Subir, Entender, Revisar, Confirmar y Resultado, con `aria-current` para comunicar el paso actual sin depender sólo del color. “Entender” explica “Indica qué significa cada columna”; el usuario puede omitir columnas no aplicables y la revisión posterior conserva la autoridad para informar faltantes.

`fallido` comunica que la importación no se completó, pero no implica que todos los pasos anteriores hayan sido completados; el contrato actual no entrega `failure stage`. En un proceso histórico fallido el stepper queda neutral y el fallo se comunica aparte, sin inventar el último paso alcanzado.

Antes de confirmar se muestran filas preparadas, filas con observaciones, destino, fuente y contexto. Los errores de fila se resumen primero por cantidad y se despliegan bajo “Ver detalles”, con límite visual. Confirmar importación es una acción explícita y no existe reintento automático. El resultado usa únicamente los campos reales devueltos por confirmación.

### Historial, detalle y zero/null/error

El historial se simplifica a Archivo/fuente, Estado, Resultado, Fecha y Ver. Los estados se traducen a copy humano y nunca se imprime snake_case como estado principal. Antes de existir un resultado se muestra “Aún sin resultado”; sólo estados completados muestran conteos de procesados y errores.

En el detalle, el estado gobierna cuándo un conteo puede considerarse resultado. `0` permanece `0` cuando el resultado existe; ausencia semántica se presenta como “Sin datos”; error de recurso se presenta como “No disponible”. El detalle separa Estado, Resumen, Errores/revisión, Origen y destino y Trazabilidad. Fuente de datos y evidencia documental permanecen visualmente separadas, con enlace al documento sólo cuando la relación explícita existe.

### Work-scoped, responsive y accesibilidad

`/obras/:obraId/evidencias` conserva el header del workspace y usa `SectionHeader`; sólo consulta el endpoint scoped de la obra y no filtra datos organizacionales en frontend para simular alcance. Las tablas mantienen overflow local, controles hacen wrap y los bloques pasan a una columna en móvil sin crear una segunda vista. File inputs tienen label accesible, stepper usa `aria-current`, enlaces y botones son elementos semánticos y errores locales usan Alert/ErrorState existentes.

### Decisiones pospuestas

PX-04 no modifica Operación, Inteligencia ni Gobernanza, no crea una experiencia de extracción documental inexistente y no expone observaciones que el contrato de evidencia no entrega. TraceabilityDrawer se conserva sin alterar su semántica. Backend permanece cerrado y PX-05 no se inicia.

## PX-05 — Operación

### Pregunta y jerarquía

Operación responde “¿qué está ocurriendo físicamente en esta unidad?” y conecta actividad real, dato observado, contexto y trazabilidad. Dentro del workspace no repite el header de la unidad: presenta sólo “Operación” y el subtexto “Revisa lo que está ocurriendo en esta unidad.”

El overview deja de representar los ocho dominios con el mismo peso. La jerarquía visible es Resumen, Requiere atención / Actividad reciente cuando existen, Dominios activos y Otros dominios. Los dominios activos son los que tienen actividad real o información que requiere revisión y se ordenan por actividad reciente cuando existe fecha comparable; no se usa score. Los dominios sin actividad, no aplicables, pendientes de configuración o no disponibles se mantienen accesibles en una presentación compacta.

### Estados y semántica

La presentación se centraliza en seis estados: Con actividad, Sin información, No aplica, Sin configurar, Requiere revisión y No disponible. Un endpoint fallido nunca se convierte en “Sin información”; una aplicabilidad `no_aplica` nunca se expresa como cero; la ambigüedad declarada por indicadores se mantiene como Requiere revisión. `0` conserva su valor real y `null` conserva ausencia de dato.

### Magnitudes y dominios sectoriales

Las magnitudes heterogéneas nunca se suman entre sí. Los dominios genéricos sólo presentan total cuando `estrategia_agregacion` es `suma`; las métricas `serie_no_aditiva` se muestran mediante cantidad de mediciones y rango cuando existe. Ruido nunca suma dB y Hídrica y suelo no fuerza totales para condiciones no aditivas. Energía, Agua, Combustibles y Residuos mantienen sus preguntas de operación y siempre presentan unidad cuando el número depende de ella.

Transporte prioriza viajes, ruta origen → destino, distancia y carga. El resumen se limita a viajes, distancia y masa transportada; combustible, vehículo, trayecto y metodología tercerizada quedan como contexto progresivo cuando el contrato los entrega. No se calculan ni infieren emisiones y no se suman métodos alternativos.

Materiales responde por entradas, usos y salidas. Los balances backend se muestran por material y unidad; el frontend deja de sumar balances de materiales distintos para crear un total artificial. Los movimientos muestran material, tipo, cantidad + unidad, lote y origen del dato sin usar IDs como información principal. Los residuos provenientes de materiales permanecen separados del flujo sectorial para evitar doble conteo visual.

### Fallos parciales, trazabilidad y alcance

`getWorkOperation` conserva `Promise.allSettled`: Transporte, Materiales y los registros sectoriales pueden fallar de forma independiente. Un fallo de una señal complementaria no invalida la actividad real que sí pudo cargarse. `OperationLayout` incorpora identidad de request para impedir que una respuesta tardía de otra obra u organización sobrescriba el scope actual.

Fuente y dato permanecen separados. Los registros ofrecen trazabilidad sólo cuando el contrato entrega fuente, evidencia o sensor; los documentos enlazan a la evidencia explícita y un origen sensor enlaza al módulo de sensores sin inferir impacto ambiental. Las rutas work-scoped existentes se mantienen y no se filtran recursos organizacionales en frontend para simular seguridad.

### Presets, responsive y accesibilidad

La prioridad del overview no se hardcodea por sector: la actividad real y la aplicabilidad gobernan la jerarquía. Las rutas especializadas de Aserradero —Recepción, Producción, Secado, Energía, Transporte forestal, Residuos/subproductos y Lotes— permanecen intactas y pueden coexistir con el workspace de unidad. Los deep links existentes no cambian.

Las cards activas reducen densidad y los otros dominios usan filas compactas; las tablas mantienen overflow horizontal local y un máximo de seis columnas visibles. Mobile apila dominios y acciones sin crear una vista paralela. Estados tienen texto, las cards navegan con `Link`, las tablas usan `th`, los detalles técnicos usan `details/summary` y el estado nunca depende sólo del color.

### Decisiones pospuestas

PX-05 no rediseña profundamente Activos ni el módulo completo de Sensores, no profundiza Indicadores, no crea ProblemáticaAmbiental automáticamente y no introduce recomendaciones, predicciones o inteligencia. Esas superficies quedan fuera de esta fase. Backend permanece cerrado y PX-06 no se inicia.

## PX-06 — Inteligencia, problemas y Copiloto

### Fronteras y pregunta de producto

Operación describe hechos; Inteligencia interpreta señales determinísticas ya producidas; Problemas gestiona una resolución verificable; Copiloto interpreta contexto preparado y propone alternativas bajo confirmación humana. Inteligencia responde “¿qué encontró el sistema que merece mi atención?”, Problemas responde “¿qué problemas estoy gestionando y en qué estado están?” y Copiloto responde “¿qué necesito entender para tomar una mejor decisión?”. Ninguna superficie autoriza a la IA a calcular CO2e, alterar resultados, seleccionar acciones, cerrar problemas o sustituir evaluaciones determinísticas.

### Inteligencia priorities-first

`/inteligencia` prioriza hasta cinco señales principales y desplaza recomendaciones y escenarios a un segundo nivel visual. Los tres recursos conservan estados independientes y una identidad de request impide mostrar contenido de una organización anterior. El frontend consume las colecciones reales `priorities`, `recommendations` y `scenarios`; no usa score cliente ni inventa urgencia. La procedencia sólo se muestra cuando el contrato la entrega, por ejemplo `source.label` en recomendaciones. Si los tres recursos están disponibles pero vacíos, la interfaz comunica “No hay señales nuevas con los datos disponibles”, sin convertir ausencia de señal en salud certificada.

### Problemas y ciclo verificable

La lista usa lenguaje operativo: Problemas, estado, riesgo, contexto y siguiente paso. Mantiene sólo búsqueda y estado como filtros visibles, separa errores de carga de errores al registrar y protege cambios de organización/obra mediante scope y request identity. La creación conserva los campos exigidos por el contrato y los agrupa en Problema y Medición inicial; en contexto de obra no vuelve a solicitar la unidad.

El detalle prioriza Siguiente paso, acción actual y resultado antes del resto de entidades. Alcance e indicadores quedan bajo disclosure. La secuencia visible es BASE → Acción → Medición → RESULT. BASE ausente nunca se convierte en cero; una acción iniciada o implementada nunca se presenta como mejora demostrada; RESULT sólo se interpreta cuando existe evaluación del servidor y las conclusiones por indicador usan el estado gobernado (`mejoro`, `empeoro`, `sin_cambio`) en vez de inferir dirección por el signo en frontend. Los ciclos anteriores permanecen en historial y una reevaluación crea un ciclo nuevo sin sobrescribir el anterior.

El flujo V2 soporta selección de acción, inicio con confirmación humana, seguimiento y evaluación. La mutación legacy de “registrar implementación” no se presenta como siguiente paso del flujo V2 porque su precondición de estado no coincide con el estado generado al iniciar una acción V2; después de iniciar, la siguiente interacción visible es seguimiento mediante una mutación que sí acepta el estado actual. La revisión profesional sólo se ofrece cuando el contrato de escalamiento puede aceptarla.

### Copiloto y confirmación humana

Copiloto trabaja sobre un único problema seleccionado. Carga de problemas, contexto y propuestas mantienen estados independientes: error de lista no equivale a cero problemas y error de contexto no produce contadores ficticios en cero. Las propuestas históricas pueden seguir visibles si falla contexto, pero no se permite preparar una nueva propuesta hasta recuperar el contexto necesario. Cambiar organización o problema invalida visualmente los recursos anteriores antes de cargar los nuevos.

Las tarjetas muestran título, explicación, estado y restricciones; requisitos, riesgos, indicadores y referencias quedan bajo “Detalles considerados”. Aceptar una propuesta se expresa como “Preparar acción”: sólo prepara una acción para confirmación posterior. La creación formal ocurre después de una confirmación humana explícita. Refutar se expresa como “Indicar por qué no aplica” y conserva la restricción/corrección como contexto; rechazar no crea una acción.

### Trazabilidad, fallos parciales y decisiones pospuestas

La trazabilidad se mantiene sólo donde existe relación explícita. Inteligencia no inventa un origen; Problemas sólo ofrece evidencia en mediciones cuando el contrato la entrega; Copiloto muestra contexto estructurado de bajo peso y no expone razonamiento interno. Los fallos parciales no derriban recursos hermanos y `0` sólo se muestra cuando proviene de un recurso cargado correctamente.

PX-06 mantiene responsive con stacks y disclosures en móvil, estados textuales, botones/enlaces reales, modales etiquetados, textarea con label, tablas con `th` y navegación por anchors semánticos. No rediseña Gobernanza ni la experiencia de revisión profesional; PX-07 permanece fuera de alcance. Backend continúa cerrado.

### Correctivo — siguiente paso y recursos conocidos

El listado de problemas no infiere mediciones, acciones o ciclos que no ha cargado. El detalle puede mostrar un siguiente paso más preciso porque sí dispone de esos recursos. Un recurso no informado permanece desconocido; una colección vacía sólo significa cero cuando fue entregada explícitamente.

## PX-07 — Gobernanza y revisión profesional

### Pregunta y jerarquía

Gobernanza responde “¿qué necesita validación profesional y qué decisiones formales ya quedaron registradas?”. La superficie deja de comportarse como un menú de herramientas: prioriza revisiones pendientes, discrepancias abiertas y expedientes que requieren antecedentes. Factores y metodologías, auditoría, conocimiento e informes permanecen accesibles como Herramientas de control secundarias.

Los tres recursos principales conservan estados independientes de carga, error y resultado. `0` sólo se muestra cuando el recurso fue cargado correctamente; un error se presenta como “No disponible” y una identidad de request evita mostrar información de otra organización.

### Revisión profesional

La cola responde “¿qué debo revisar y decidir?”. Mantiene únicamente Tipo y Estado como filtros, usa los tipos y estados reales del contrato y reduce cada fila a elemento, estado, fecha, hallazgos, profesional y siguiente acción. Cuando el contrato no entrega un nombre humano del objeto revisado, la UI usa un fallback honesto por tipo e ID técnico secundario.

Hallazgo y decisión permanecen separados. Registrar un hallazgo no cambia automáticamente el estado de la revisión. Una decisión formal exige una confirmación explícita y comunica que quedará registrada sin sobrescribir antecedentes históricos. Revisiones decididas son de solo lectura; el modo demo mantiene toda la cola en solo lectura y lo comunica al usuario. Los errores de mutación son locales y no reemplazan el listado cargado.

### Expedientes y validación

Un expediente se presenta como un paquete gobernado de antecedentes de un problema, no como una carpeta genérica. El listado prioriza problema, estado, revisión profesional, informe vigente, fecha y acceso. El detalle usa el snapshot real de `referencias` y resume antecedentes por sus relaciones explícitas; no reconstruye objetos ni nombres que el contrato no entrega.

El estado del expediente y la validación profesional son dimensiones distintas. Un expediente cerrado, completo según su flujo o con informe vigente no se presenta automáticamente como validado por un profesional. La validación profesional sólo se comunica cuando existe una revisión cuyo estado contractual es `validada` o `validada_con_observaciones`. La creación, cierre, reapertura, generación de informes y eventos de auditoría permanecen versionados/históricos.

### Calidad, discrepancias y responsabilidad

Calidad del dato y confiabilidad de fuente permanecen separadas. Una política de prioridad de fuente no convierte automáticamente un dato en válido. Las discrepancias abiertas son únicamente las que el contrato representa como `detectada` o `requiere_revision`; el frontend no trata toda discrepancia recibida como abierta ni resuelve contradicciones por su cuenta.

Auditoría se presenta como historial verificable de fecha, actor, acción, elemento y contexto, sin ofrecer edición o borrado. Conocimiento usa los casos reales y su procedencia verificable; los estados `utilizable` y `candidato`, la fuerza de evidencia y el origen permanecen explícitos. La IA nunca aparece como validador profesional ni una propuesta de IA se transforma visualmente en decisión humana.

### Partial failures, stale guards y decisiones pospuestas

Overview, calidad y conocimiento preservan fallos parciales; una fuente secundaria que falla no derriba las demás. ReviewQueue, expedientes, detalle, auditoría y conocimiento invalidan visualmente el scope anterior durante cambios de organización, objeto o filtros. Las rutas y navegación existentes permanecen como autoridad y Factores y metodologías continúa integrado bajo Gobernanza sin rediseño profundo.

PX-07 no rediseña Administración, usuarios ni configuración profunda. Backend permanece cerrado y PX-08 no se inicia.

### Correctivo — conteos y alcance de filtros

Los conteos mostrados en Revisión profesional respetan el alcance de los filtros activos; un subconjunto filtrado no se presenta como total global de revisiones pendientes. Sin filtro de tipo y con Estado = Pendiente se muestra el total del conjunto pendiente consultado; con Tipo activo o con un Estado específico distinto de Pendiente la metadata se expresa como resultados del subconjunto. Con Tipo = Todos y Estado = Todos, la colección contiene todos los estados y permite calcular localmente cuántas revisiones están pendientes. Un error de consulta no muestra conteos.

## PX-08 — Administración

### Alcance y frontera con Gobernanza

Administración responde “¿Cómo está configurada mi organización y quién puede hacer qué?” y agrupa Organización, Usuarios y roles, Preferencias, Estructura y Diagnóstico. Organización, personas y opciones operativas permanecen aquí; factores, metodologías y decisiones profesionales continúan en Gobernanza y sólo se enlazan cuando aporta contexto.

### Organización y usuarios

Organización es la autoridad visual para identidad y perfil de operación. Seleccionar una organización cambia el contexto de trabajo y permanece separado de editar sus datos. El alta solicita una identidad mínima y no expone identificadores técnicos. El perfil de operación puede modificarse porque el contrato lo permite, pero la UI comunica que reorganiza vocabulario y composición antes de guardar. La eliminación usa confirmación explícita y comunica su alcance destructivo real.

Usuarios y roles responde quién tiene acceso. Usa únicamente los roles contractuales Administrador, Analista, Operador y Lector; no transforma el rol en una lista inventada de permisos. Agregar usuario crea el acceso inmediatamente según el contrato actual, por eso no se presenta como invitación. El usuario actual se identifica como “Tú” cuando coincide de forma verificable. Carga y mutación conservan errores separados y los cambios de organización invalidan la lista anterior.

### Preferencias operativas y configuración científica

`/administracion/configuracion` se presenta como Preferencias y consume directamente la configuración confirmada de la organización. La superficie principal conserva preferencias contractuales de importación, documentos y presentación de reportes. Parámetros científicamente sensibles como factor eléctrico, unidad de cálculo o reglas metodológicas no se presentan como preferencias administrativas; los defaults históricos de carbono, densidad, scores y umbrales que sólo existían en frontend se retiran de la experiencia visible sin borrar almacenamiento del servidor.

La configuración remota es la única autoridad. Una copia en `localStorage` puede conservarse como respaldo, pero ante fallo de la carga remota sólo se comunica como copia local no confirmada y no habilita edición ni guardado. “Preferencias guardadas” aparece únicamente después de una respuesta exitosa del servidor. “Cargar valores sugeridos” modifica sólo campos administrativos visibles y no se presenta como restauración de valores oficiales. Los cambios sin guardar se hacen visibles.

### Diagnóstico, estructura y seguridad de contexto

Diagnóstico se limita a contexto organizacional, información disponible o pendiente, aplicabilidad y la preparación que entrega el servidor; deja de crear unidades y procesos dentro de la misma pantalla. Sus recursos principales cargan de forma independiente y nunca completan ausencias con supuestos.

Estructura deja de funcionar como dashboard ambiental y presenta la organización operacional registrada. Construcción puede crear etapas usando el contrato existente; otros perfiles no reciben una taxonomía de etapas de obra por defecto. Usuarios, Preferencias, Diagnóstico y Estructura invalidan el scope anterior al cambiar de organización. El modo demo mantiene las mutaciones administrativas en sólo lectura.

PX-08 conserva las rutas existentes, reutiliza el design system compartido, mantiene tablas con overflow local y stacks en móvil. Backend permanece cerrado. PX-09 no se inicia.
