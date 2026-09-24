# Decisions

Este archivo registra decisiones importantes ya tomadas. Las ideas exploratorias deben quedarse en su documento correspondiente o en [[INBOX]] hasta que se conviertan en decision.

## 2026-09-16 - Separar importacion y verificacion de ensayos

### Decision

El procesamiento de ensayos tendra etapas separadas:

1. Etapa 1: PDF a `draft.json`, `assets/` y `evidence/`.
2. Etapa 2: verificacion independiente del borrador contra el PDF, con salida posterior `verified.json`.
3. Enriquecimiento posterior: contenido verificado a `final.json` y luego al banco.

La Etapa 1 no resuelve preguntas, no asigna eje, habilidad o dificultad y no genera explicaciones pedagogicas.

### Razon

Separar extraccion de verificacion permite rastrear el origen de cada bloque y evita que una respuesta o clasificacion de IA altere silenciosamente el contenido original.

### Consecuencia

`draft.json` debe conservar texto, matematicas, figuras, tablas, regiones, assets, evidencia e incidencias. Debe poder ser revisado despues por ejecuciones independientes sin reprocesar el PDF completo.

### Estado

Aceptada

## 2026-09-16 - IA bajo demanda para reconstruccion del importador

### Decision

La Etapa 1 seguira una politica local-first, AI-on-demand. Primero ejecutara extraccion, OCR, renderizado, crops, segmentacion y validaciones locales. El modelo del CLI del usuario solo intervendra cuando exista una ambiguedad real de reconstruccion.

La IA recibira preferentemente texto, regiones o crops. Solo recibira una pagina completa cuando falte contexto. La skill registrara proveedor o CLI, bloque afectado, evidencia enviada y cambio producido. La IA no resolvera ni clasificara preguntas en esta etapa.

### Razon

Reduce envio de material, coste y dependencia de servicios externos, y mantiene separadas las tareas mecanicas de las interpretativas.

### Consecuencia

La skill usa un contrato de solicitud y respuesta para el CLI anfitrion, sin adaptadores separados por proveedor. Si no hay capacidad adecuada, conserva el bloque como `unresolved` y registra una incidencia. Procesamiento local no significa que un modelo remoto sea privado: cada uso debe quedar explicito.

### Estado

Aceptada

## 2026-09-16 - Skill y herramientas base de Etapa 1

### Decision

La ubicacion canonica interna de la skill es `skills/paes-importer/`. `pypdfium2` es el renderizador principal para paginas y crops PNG. OCR permanece opcional y se reserva para cuando la extraccion local lo requiera.

El procesamiento seguira local-first + AI-on-demand: primero herramientas locales; despues modelo del CLI del usuario solo para ambiguedades reales. Se enviaran crops o texto antes que paginas completas.

### Razon

Una skill real desde el inicio evita construir un prototipo desechable. PDFium conserva texto, imagenes y trazos vectoriales al renderizar regiones; OCR no debe añadir dependencias ni coste cuando el PDF ya tiene texto util.

### Consecuencia

El benchmark inicial usara ocho preguntas reales de los dos PDFs registrados en [[PROJECT_CONTEXT]]. No se implementaran todavia verificadores, workers, batches ni adaptadores multi-CLI.

### Estado

Aceptada

## 2026-09-16 - MVP gratuito, sin publicidad y open source

### Decision

El MVP sera gratuito, no mostrara publicidad y mantendra su codigo y documentacion propia como open source. Una posible monetizacion futura queda sin decidir.

### Razon

La primera etapa debe validar el aprendizaje y la utilidad del producto sin crear barreras de acceso ni distraer al estudiante.

### Consecuencia

El MVP no incluira pagos, anuncios ni seguimiento publicitario. Cualquier modelo comercial futuro debera evaluarse por separado y no podra asumir derechos comerciales sobre contenido de terceros.

### Estado

Aceptada

## 2026-09-16 - Taxonomia M1 y prerrequisitos blandos

### Decision

La taxonomia del MVP usara 4 ejes y 16 unidades del temario PAES Regular M1 Admision 2027. Las 4 habilidades DEMRE seran etiquetas transversales: cada pregunta tendra una habilidad primaria y podra tener una secundaria.

Los prerrequisitos serviran para recomendar repasos. No bloquearan unidades ni exigiran pruebas de desbloqueo. Podran existir relaciones entre ejes cuando sean pedagogicamente claras.

### Razon

Esta estructura conserva el temario oficial sin crear decenas de microtemas. Las recomendaciones blandas ayudan al estudiante con base debil sin impedir que un estudiante avanzado practique libremente.

### Consecuencia

Todo el catalogo permanece accesible. Las relaciones iniciales deben validarse contra preguntas oficiales permitidas y durante el piloto. El catalogo se versionara para no modificar historiales cuando DEMRE cambie el temario.

### Estado

Aceptada

## 2026-09-16 - Diagnostico inicial de doce preguntas

### Decision

El diagnostico inicial del MVP tendra 12 preguntas fijas y apuntara a una duracion maxima de 15 minutos. Se balanceara con 3 preguntas por eje y 3 por habilidad primaria. Cada eje tendra una pregunta basica, una intermedia y una avanzada.

Al terminar, se mostraran inmediatamente porcentajes aproximados por eje y habilidad, identificados como **resultado inicial aproximado**. La practica guiada y el ensayo completo los recalibraran con nueva evidencia.

### Razon

Doce preguntas permiten cubrir los cuatro ejes simetricamente y dan aproximadamente 75 segundos por pregunta. Quince preguntas reducirian el tiempo a un minuto por ejercicio, aumentando fatiga, respuestas al azar y abandono en estudiantes con base debil.

El estudiante necesita comprender el resultado inmediatamente. Una etiqueta clara permite mostrar porcentajes utiles sin presentarlos como una medicion definitiva.

### Consecuencia

No habra bandas bloqueadas, contador de evidencias ni porcentajes ocultos. El resultado inicial no se convertira en una estimacion de puntaje PAES.

### Estado

Aceptada

## 2026-09-16 - Piloto inicial con cinco estudiantes

### Decision

El primer piloto comenzara con 5 estudiantes reales de confianza. Si el recorrido principal funciona sin bloqueos graves, se invitara progresivamente a mas estudiantes.

### Razon

Un grupo pequeno permite observar problemas de comprension y funcionamiento antes de ampliar la prueba.

### Consecuencia

El piloto evaluara si cada estudiante completa el test corto, comprende su principal debilidad, inicia la nivelacion y reconoce su siguiente leccion. Tambien registrara errores y puntos de confusion.

### Estado

Aceptada

## 2026-09-16 - Alcance funcional del primer MVP

### Decision

El primer MVP incluira Inicio, Aprender, un test diagnostico corto, nivelacion, estadisticas de fortalezas y debilidades, un ensayo PAES completo opcional dentro de la web, PAES Scanner y Verificador.

Playground y Ranking apareceran como Proximamente. Los pagos no forman parte del alcance confirmado.

### Razon

El producto debe cubrir el ciclo de deteccion, nivelacion y reevaluacion, y permitir incorporar ensayos externos sin mezclar todavia practica libre ni competencia.

### Consecuencia

Scanner y Verificador dejan de ser expansiones posteriores y deben especificarse antes de implementar el MVP. Playground y Ranking no deben bloquear el recorrido principal.

### Estado

Aceptada

## 2026-09-16 - Evaluacion progresiva y recalibracion

### Decision

El estudiante comenzara con un test diagnostico corto dentro de la web. Inicio mostrara un aviso superior descartable para ofrecer un ensayo PAES completo opcional. El ensayo completo agregara evidencia y recalibrara el perfil sin borrar el progreso anterior.

### Razon

El test corto reduce la friccion inicial. El ensayo completo permite mejorar posteriormente la calidad de las estadisticas y recomendaciones.

### Consecuencia

Las estadisticas deben distinguir evidencia preliminar de evidencia mas completa. El producto no debe presentar porcentajes como mediciones exactas cuando falten datos.

El test corto se interpretara por eje y habilidad. Se usara inicialmente 80% como umbral entre nivelacion y repaso, sujeto a validacion durante el piloto. La practica guiada agregara evidencia y recalibrara el perfil.

### Estado

Aceptada

## 2026-09-16 - Ensayos externos editables y Ranking aislado

### Decision

Los ensayos externos procesados mediante PAES Scanner y revisados en Verificador podran recalibrar el perfil. El usuario podra corregir errores de lectura o preguntas defectuosas antes de confirmar los resultados.

El futuro modo Ranking usara solamente preguntas diarias controladas por el sistema. Sus respuestas confirmadas no seran editables y los ensayos externos no otorgaran puntos competitivos.

### Razon

Las importaciones automaticas pueden contener errores, mientras que una clasificacion competitiva necesita resultados comparables y no manipulables.

### Consecuencia

El sistema debe conservar diferencia entre datos importados, correcciones y resultados confirmados. Ranking permanece fuera del primer MVP.

### Estado

Aceptada

## 2026-09-15 - PAESSED sera codigo abierto

### Decision

El proyecto se publicara como codigo abierto en GitHub.

### Razon

Permite respaldar el trabajo, transparentar las bases del producto y facilitar colaboracion externa.

### Consecuencia

El repositorio debe mantener archivos base de comunidad, licencia, seguridad, contribucion y politicas claras para evitar subir datos privados, secretos o contenido sin permiso.

### Estado

Aceptada

## 2026-09-15 - Licencia MIT para el repositorio

### Decision

El codigo y la documentacion propia del proyecto se publicaran bajo licencia MIT.

### Razon

Es una licencia permisiva, simple y comun para proyectos abiertos en etapa temprana.

### Consecuencia

La licencia aplica al trabajo propio del repositorio, pero no concede permisos sobre materiales de terceros como preguntas oficiales, ensayos privados, PDFs, imagenes externas o bancos de contenido.

### Estado

Aceptada

## 2026-09-15 - No versionar contenido privado o protegido

### Decision

El repositorio no debe incluir PDFs privados, datos reales de estudiantes, secretos ni contenido educativo sin permiso claro de uso y redistribucion.

### Razon

El proyecto es educativo y open source, por lo que debe proteger privacidad, derechos de autor y confianza de colaboradores.

### Consecuencia

Los ejemplos deben ser sinteticos o estar claramente autorizados. Antes de agregar contenido se debe revisar [[docs/DATA_AND_CONTENT_POLICY]].

### Estado

Aceptada

## 2026-09-14 - Separar Aprender y Playground

### Decision

Aprender sera guiado por el sistema. Playground sera controlado libremente por el usuario.

### Razon

Son necesidades diferentes: una experiencia orienta el aprendizaje y la otra permite practica libre.

### Consecuencia

Probablemente sus resultados tendran distinto peso en el sistema de dominio.

### Estado

Aceptada

## 2026-09-14 - El diagnostico puede modificar el punto inicial de la ruta

### Decision

Los estudiantes no necesariamente comienzan desde la primera leccion.

### Razon

No tiene sentido obligar a un estudiante avanzado a completar contenido que ya domina.

### Consecuencia

Necesitamos dominio por habilidad y no solamente un nivel global.

### Estado

Aceptada

## 2026-09-14 - Contenido privado local-first

### Decision

Los ensayos externos privados no se almacenaran como banco publico de la plataforma.

### Razon

Privacidad y derechos de autor.

### Consecuencia

El procesamiento se realizara localmente y la web importara una representacion estructurada.

### Estado

Aceptada

### Crear el logo
Logo creado en afinity en vector y exportado en png en C:\Users\Administrator\Documents\Paessed.cl

## 2026-09-16 - Refactor generico del importador Etapa 1

El pipeline de skills/paes-importer/ queda organizado como inventario posicional completo, deteccion de candidatos por geometria, reconstruccion tipada, control de cobertura y generacion de draft.json. Math, visuales y tablas no pueden depender de question_id ni de identificadores ImN.

Las barras, numeradores/denominadores, superindices y raices se reconstruyen solo cuando la geometria es demostrable; de lo contrario se conserva un bloque unresolved. Las imagenes y regiones visuales se asocian por posicion respecto del stem y las alternativas. Las tablas se estructuran solo con una rejilla verificable; en caso contrario se usa un fallback visual fiel.

complete exige cobertura estructural satisfactoria. La IA del CLI se reserva para candidatos locales ambiguos y solo transcribe o reconstruye estructura: no resuelve, explica ni clasifica preguntas. run-holdout-v1 y su seleccion permanecen congelados como regresion.
\n

## Decisión: cobertura por objetos y ruta única - 2026-09-16

La arquitectura de Etapa 1 adopta source_objects como inventario auditable y exige propiedad estructural exclusiva. complete requiere que cada objeto relevante tenga una representación o un unresolved explícito; la validez sintáctica del LaTeX no certifica cobertura. Las preguntas de desarrollo y holdout deben ejecutar la misma ruta genérica; los reconstructores históricos solo sirven como oracle durante la migración.

La regresión actual se conserva en nuevos directorios (run-generic-v1 y run-holdout-regression-v3); run-holdout-v1 y su selección permanecen intactos. Las preguntas parciales no se reparan automáticamente ni se promueven a complete.

## Decision: consumidores y cobertura estructural - 2026-09-16

Se implementa source_objects como inventario auditable por objeto de origen. Cada entrada incluye id estable, region_id, owner estructural, candidate_type, bbox, representation y consumers. La completitud no se decide por coincidencia de cadenas LaTeX: exige consumo unico, propietario compatible y ausencia de unresolved anidado. Un candidato matematico, visual o de tabla puede existir sin reconstruccion; en ese caso se conserva como unresolved y la pregunta queda partial.

La evaluacion usa una unica ruta generica para desarrollo y holdout. Los reconstructores antiguos no participan en draft.json y se conservan como oracle. Las tablas procesan tambien el contenido interno de sus celdas. La asociacion ambigua de una alternativa queda fuera de todos los propietarios y se registra como unresolved con incidencia bloqueante.

Resultados historicos (superados por la validacion de fidelidad descrita abajo): desarrollo generico 7/8 complete y P38 partial; holdout de regresion 7/8 complete y P35 partial. Se mantienen intactos run-holdout-v1 y su seleccion.

## Decision: cobertura no equivale a fidelidad - 2026-09-16

Ademas del consumo unico de objetos, complete requiere validacion de orden inline, tipo y relaciones de expresion. Una fraccion y un exponente consumidos por separado no prueban una expresion correcta. Los candidatos conectados no demostrados quedan como un unresolved atomico con source_ids, candidate_id, propuestas conservadas y solicitud AI-on-demand pendiente. No se llama a IA automaticamente ni se usa confianza del modelo para completar.

La ruta generica incorpora structural_fidelity.py sin ramas por pregunta. Los tests de integracion ejecutan el CLI actual sobre ambos conjuntos; los tests oracle no certifican esta ruta. Resultados de esta validacion inicial: desarrollo 3 complete / 5 partial; regresion 6 complete / 2 partial. La reduccion de complete expone pendientes antes ocultos, no significa que se hayan reconstruido todas las formulas. Ver [[technical/STRUCTURAL_FIDELITY_REVIEW]]. En esta validacion no se ejecuto holdout-v2 ni el ensayo completo.

## Decision: aritmetica simple y AI-on-demand - 2026-09-17

Se amplia la ruta generica solo para aritmetica numerica inline y ecuaciones inline simples. Se preserva el texto alrededor mediante spans de origen derivados, sin calcular ni simplificar. Sistemas, composiciones simbolicas y agrupaciones ambiguas siguen unresolved.

Los candidatos pendientes generan un crop minimo de evidencia. El CLI anfitrion recibe ese crop y una instruccion estricta, y devuelve schema/ai-response.schema.json. El aplicador valida candidate_id, propietario, source_ids exactos y tipo; registra cli, model, objetivo, evidencia y resultado en extraction.ai_interventions; sustituye solo el candidato y recalcula coverage, structural fidelity y status. La salida de IA nunca fuerza complete: si la fidelidad no queda demostrada, permanece partial.

No se implementan adaptadores separados para Codex, Claude o AGY. En esta iteracion no se procesaron holdout-v2 ni 65 preguntas.

## Seguimiento de Etapa 1 - 2026-09-23

La skill y el importador generico de Etapa 1 estan implementados. Las corridas registradas de ocho preguntas muestran: Development 5 `complete` / 3 `partial`; holdout-v1 6 / 2; holdout-v2 sobre Ensayo 326 1 / 7; Tesla 0 / 8; y Matematica (1) 1 / 7. Holdout-v2 fue una primera ejecucion parcial de ocho preguntas del ensayo de 65.

En la corrida de Matematica (1), Q10 quedo `partial` y Q19 `complete`. El checkpoint Q10/Q19 se cerro en `4c244a0` y se publico en `origin/main`. La verificacion independiente de Etapa 2 y el enriquecimiento a `final.json` siguen pendientes.
