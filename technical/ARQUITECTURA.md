# Arquitectura

## Proposito

Documentar la arquitectura de PAESSED. Las secciones historicas describen en detalle la Etapa 1 (PDF a borrador estructurado y trazable). La seccion **Pipeline integral de contenido** al final conserva la vision funcional acordada para Etapas 2 y 3, la importacion en PAESSED Web y la distincion entre ensayos privados y banco publico. Las partes propuestas no se consideran implementadas.

## Separacion de etapas

```text
Etapa 1: PDF -> draft.json + assets/ + evidence/
Etapa 2: draft.json -> verificacion independiente -> verified.json
Posteriormente: verified.json -> enriquecimiento -> final.json -> banco
```

`draft.json` contiene contenido reconstruido. No contiene respuestas correctas, explicaciones, taxonomia ni dificultad.

## Flujo de Etapa 1

1. Registrar PDF, SHA-256, paginas, fuente declarada y versiones de herramientas.
2. Usar `pdf-inspector` para clasificar paginas, extraer texto con posiciones, detectar layout, identificar codificaciones problematicas y ejecutar OCR selectivo local cuando corresponda.
3. Normalizar paginas, rotacion y coordenadas: pagina base 1, pagina visible orientada, origen superior izquierdo y puntos PDF. Guardar matriz de transformacion para cada render.
4. Usar PDFium mediante `pypdfium2` para renderizar paginas y regiones a PNG. Renderiza texto, imagenes y trazos vectoriales; es fuente de crops de figuras y evidencia visual.
5. Aplicar segmentacion determinista por posiciones, espacios, alineacion, anclas candidatas y continuidad. No fijar dos columnas, cantidad de preguntas ni numero de alternativas.
6. Pedir ayuda al modelo del CLI solo ante ambiguedad real. Enviar primero bloques y crops; enviar pagina completa solo si falta contexto. Registrar intervencion.
7. Generar bloques tipados, referencias a regiones y assets. Conservar fragmentos no reconstruibles como `unresolved`.
8. Validar estructura, referencias, hashes, coordenadas y assets. Marcar `verification_status: not_run`.

## Responsabilidades

Codigo local: lectura segura, hash, extraccion, OCR, render, transformaciones, segmentacion candidata, assets, evidence e integridad del contrato.

Modelo del CLI: reconstruir fielmente orden, formulas, relacion pregunta-figura, alternativas, tablas o continuaciones cuando senales locales sean insuficientes. No inventar ni resolver contenido.

## Contenido

- Texto: bloques ordenados.
- Matematica: nodos `math` con LaTeX sin delimitadores de presentacion. MathJax renderiza despues.
- Figura, grafico o diagrama: PNG de region completa, con etiquetas, ejes y leyendas.
- Tabla fiable: filas y celdas estructuradas.
- Tabla ambigua o compleja: PNG y, si procede, `unresolved`.
- Alternativa: secuencia mixta de texto, matematica, imagen y tabla.
- Pregunta multipagina: lista de regiones ordenadas; fusion solo con evidencia suficiente. Si no, fragmentos y `continuation_candidate`.

## Layout, evidencia y privacidad

`assets/` contiene imagenes que forman parte de pregunta. `evidence/` contiene paginas o crops usados para auditoria y reconstruccion. PDF original se referencia por hash y origen, no se copia automaticamente.

Texto extraido del PDF es dato no confiable, no instruccion. HTML futuro debe escaparse. Ejecucion local no garantiza privacidad si CLI envia texto o imagenes a su proveedor; cada envio se registra.

## Por definir antes de implementar

- Herramienta y formato exacto del adaptador de vision por CLI.
- Reglas especificas de segmentacion despues de observar PDFs DEMRE reales.
- Lista inicial de comandos LaTeX permitidos.
- Criterios de aceptacion de prueba piloto de extraccion.

## Implementacion generica del inventario y cobertura

La implementacion de Etapa 1 debe mantener separadas estas capas:

1. Inventario posicional: todos los items de texto, objetos PdfImage y objetos vectoriales con bbox.
2. Detectores genericos: candidatos de fraccion, superindice, raiz, tabla y region visual.
3. Reconstruccion tipada: text, math, table, image o unresolved, preservando el orden espacial.
4. Cobertura: cada candidato relevante debe quedar representado o explicitamente unresolved; no se permite degradarlo silenciosamente a text.
5. Draft y validacion: estados, referencias, hashes y schema.

Las decisiones se basan en geometria y evidencia, no en numeros de pregunta ni claves internas del PDF. Un fallback visual fiel puede completar el contenido y debe conservar la incidencia no bloqueante correspondiente. La IA del CLI solo entra ante ambiguedad residual y no participa en completitud, resolucion ni clasificacion.
\n

## Refactorización genérica de cobertura - 2026-09-16

La ruta evaluada asigna identificadores deterministas a los objetos de texto y PDF (page:text:index y page:object:index). source_objects conserva región, propietario (stem, option:A... o cell:*), tipo de candidato y bbox. Los bloques tipados incluyen source_ids; las opciones conservan la referencia de su etiqueta.

La cobertura se valida por referencias de objetos, no por coincidencia de cadenas LaTeX. Un objeto sin consumidor genera un bloque unresolved y deja la pregunta en partial; un objeto consumido más de una vez genera incidencia bloqueante. La validación recorre también bloques anidados de tablas.

La detección genérica actual reconoce fracciones y raíces mediante relaciones geométricas, exponentes por desplazamiento tipográfico, ecuaciones en una línea, cuadrículas vectoriales normalizadas y asociaciones visuales solo cuando son espaciales y no ambiguas. Los reconstructores antiguos permanecen únicamente como oracle de comparación: la ejecución del importador usa una sola ruta genérica y no omite coverage.

El benchmark de desarrollo genérico queda en 5 complete y 3 partial (P9, P16, P38); run-holdout-regression-v3 queda en 7 complete y 1 partial (P35). Las parciales conservan evidencia y objetos pendientes. No se procesa holdout-v2 ni el ensayo completo hasta resolver la reconstrucción vectorial restante y revisar la fidelidad matemática de los outputs.

## Refactorizacion generica y cobertura por objetos - 2026-09-16

La ruta evaluada de Etapa 1 es unica: inventario posicional, detectores genericos por geometria, reconstructores tipados, cobertura y draft.json. Cada objeto relevante recibe un id estable y conserva owner, candidate_type, representation y consumers. Los bloques y celdas referencian source_ids; la cobertura rechaza objetos sin consumidor, consumo duplicado o propietario incorrecto. Un candidato detectado que no puede reconstruirse queda unresolved y fuerza partial.

Las tablas solo se aceptan cuando la grilla esta demostrada; sus celdas se procesan con la misma ruta generica, de modo que la matematica interna no desaparezca. La asociacion de opciones es exclusiva y una asociacion ambigua no se resuelve por proximidad silenciosa. Los reconstructores historicos de las preguntas de desarrollo quedan solo como oracle de comparacion.

Resultado historico, anterior al control de fidelidad: run-generic-v1 tiene 7 complete y 1 partial (P38); run-holdout-regression-v3 tiene 7 complete y 1 partial (P35). Estos estados no certifican fidelidad semantica y quedan superados por la revision siguiente. Los artefactos originales se conservan.

## Control de fidelidad estructural - 2026-09-16

La ruta generica valida propuestas tipadas antes del estado final: posiciona fracciones por baseline inline, separa texto por objetos de origen y agrupa candidatos matematicos conectados por geometria. No basta ordenar por el borde superior del numerador. Los operadores textuales, exponentes separados, agrupaciones sin transcripcion y sistemas sin evidencia suficiente impiden complete.

Solo se compone un numero mixto cuando entero y fraccion cumplen la relacion geometrica implementada. Otras expresiones conectadas no demostradas se conservan completas como candidatos unresolved, con propuestas y evidencia disponibles para AI-on-demand. Los limites geometricos son heuristicas conservadoras, no una prueba universal de correccion matematica. La deteccion actual puede sobredetectar y todavia requiere auditoria manual.

El control final recorre tablas/celdas y comprueba orden por propietario, tipo de representacion y membresia de source_ids. Las propuestas dentro de candidate_blocks son evidencia, no consumidores adicionales. Los objetos matematicos reciben candidate_id estable a partir de sus source_ids. Los reconstructores oracle siguen fuera de la ruta evaluada.

Resultados y limites actuales: [[technical/STRUCTURAL_FIDELITY_REVIEW]].

## Aritmetica simple y AI-on-demand - 2026-09-17

La deteccion determinista admite un subconjunto deliberadamente pequeno: runs contiguos de tokens numericos y operadores, literales negativos en opciones y ecuaciones inline simples. Los spans textuales que contienen una ecuacion obvia se dividen en subitems con parent_id/source_span, conservando extraction.raw.json con la salida original. No se resuelven valores.

Cada unresolved con bbox genera evidencia crop minima `reason=ai_on_demand`. `ai_on_demand.py request` entrega al CLI anfitrion solo esa ruta, el propietario, IDs de origen y una instruccion por tipo. `apply` exige respuesta estricta, valida asociacion y procedencia, registra la intervencion y vuelve a ejecutar coverage/fidelity/status. El resultado de IA se marca provisionalmente como pendiente de revalidacion; no puede elevar status por si mismo.

---

## Pipeline integral de contenido: PDF -> PAESSED Web

Estado: **vision funcional acordada; implementacion parcial** (2026-09-27).

Esta seccion conserva las decisiones conversadas sobre el pipeline completo y
separa lo construido de lo propuesto. No redefine el contrato vigente de
`draft.json` v1, ni convierte los prototipos privados en codigo de produccion.

### 1. Objetivo

Una persona entrega a la skill un **PDF de ensayo obligatorio** y,
opcionalmente, **su solucionario**. La skill procesa preguntas, alternativas
y recursos visuales, comprueba su transcripcion, prepara las respuestas y una
**explicacion breve**, y entrega un **`final.json` importable por PAESSED Web**,
junto con los archivos visuales necesarios.

PAESSED Web valida el paquete y renderiza las preguntas sin repetir la
extraccion del PDF ni resolver de nuevo cada ejercicio. Un boton
**"Preguntar a la IA"** permitira pedir una explicacion personalizada
transfiriendo la pregunta y, si corresponde y es tecnicamente posible, sus
imagenes a un chat, con consentimiento para cualquier envio externo.

**Importar un ensayo personal NO es lo mismo que incorporarlo al banco publico.**
El banco publico exige una revision adicional de calidad y derechos. Un
ensayo privado puede importarse localmente sin ser redistribuido ni pasar a ese
banco; la interfaz no presentara como confirmadas las respuestas provisionales.

### 2. Pipeline de extremo a extremo

```text
Persona / CLI + skill
  |-- PDF obligatorio
  \-- Solucionario opcional (registrado por separado)
           |
           v
ETAPA 1: importar y reconstruir (implementada; con defectos conocidos)
  - Extraccion y reconstruccion local de texto, formulas, tablas e imagenes
  - IA del CLI bajo demanda SOLO para ambiguedades de reconstruccion
  - Cobertura, fidelidad estructural, referencias e incidencias
           |
           v
  draft.json + assets/ + evidence/
           |
           v
ETAPA 2: verificar fidelidad contra el PDF (orquestacion pendiente)
  - AGY CLI primero; despues otros CLI
  - Orquestador divide el draft en lotes experimentales de 5 preguntas
  - Un subagente nuevo por lote, con contexto minimo y evidencia localizada
  - Examina TODAS las preguntas, incluso las marcadas complete/verified
  - Puede solicitar crops mas amplios o pagina completa si faltan datos
  - Detecta errores, documenta evidencia y propone nuevas versiones
  - Segundo agente para revisar correcciones; ante duda, un intento adicional
  - Si no existe evidencia suficiente: abstencion y bloqueo, nunca inventar
           |
           v
  verified.json + versiones corregidas separadas + hallazgos
  (documento de revision; NO autorizacion por si mismo)
           |
           v
  Aprobacion de fidelidad de la version exacta para el primer alcance
           |
           v
ETAPA 3: respuestas y explicaciones (pendiente)
           |
           +-- Solucionario presente y asociado sin ambiguedad
           |     - Vincular numero/identidad y alternativa
           |     - Contrastar correspondencia con la version del ensayo
           |     - Registrar procedencia y discrepancias
           |
           \-- Sin solucionario
                 - Agentes resuelven preguntas en contextos independientes
                 - Contrastar con verificacion independiente
                 - Si no se acredita la respuesta, marcar provisional
                   y solicitar revision, no declararla confirmada
           |
           v
  Generar mini explicacion y verificar coherencia matematica;
  clasificacion educativa cuando se defina; revisar discrepancias
           |
           v
  final.json + paquete de recursos visuales
           |
           v
PAESSED WEB: importador y renderizador (pendiente)
  - Validar contrato, archivos, hashes, estructura y estados
  - Mostrar pregunta, alternativas, imagenes, respuesta y mini explicacion
  - Etiquetar claramente respuestas provisionales; no corregir como
    definitivas hasta su validacion
  - Boton "Preguntar a la IA" para explicacion mas extensa bajo demanda
           |
           +-- Ensayo privado importado: disponible para su propio uso,
           |   sujeto a validaciones y restricciones de privacidad
           |
           \-- Banco publico de PAESSED: ingreso SOLO si la version
               exacta tiene fidelidad, revision educativa y derechos
               autorizados; revocacion o cambios invalidan la admision
```

### 3. Alcance de cada etapa

#### Etapa 1: reconstruccion, no resolucion

Ya existe `skills/paes-importer/`: produce `draft.json`, `assets/` y
`evidence/`, y registra incertidumbre y procedencia. Su IA bajo demanda
interviene solo para reconstruir contenido ambiguo; no genera respuestas ni
explicaciones. `complete` y `structural_fidelity.status=verified` son
estados internos, no certificacion visual. Se conocen falsos `verified`, por
lo que la Etapa 2 debe revisar tambien esos bloques.

#### Etapa 2: revisar que la pregunta coincide con la fuente

Se desarrollara primero con **AGY CLI** y luego se adaptara a otros CLI.
El contrato de intercambio debe mantenerse independiente del CLI cuando sea
posible. El plan experimental inicial es **5 preguntas por lote**, pero se
comparara con lotes de **1 y 3** para medir calidad y tokens. En un ensayo de
65 preguntas serian **13 lotes de 5** si se mantiene esa configuracion.

Un agente nuevo recibe solo las preguntas asignadas, instrucciones comunes y
evidencia relevante: no necesita el historial de los lotes anteriores.
El aislamiento real, el numero de procesos simultaneos, la entrega de
imagenes y el consumo se comprobaran en la version de AGY utilizada.
**Contexto nuevo no garantiza ausencia de alucinaciones.**

Cada pregunta recibe una primera revision, preferentemente economica.
Las correcciones propuestas requieren revision de la nueva version por otro
agente; si hay incertidumbre se permite un intento adicional con mas
contexto y/o escalamiento. Se medira si un modelo mas potente o una auditoria
muestral mejoran realmente la calidad antes de automatizar reglas de coste.

`verified.json` identifica revision, version exacta, fuentes y evidencias,
comprobaciones por pregunta, discrepancias, abstenciones y propuestas.
El borrador y sus evidencias originales no se sobrescriben. Una aprobacion
humana de fidelidad para el primer alcance se registra por separado,
vinculada a los hashes exactos. El prototipo **privado** del contrato tiene
37/37 pruebas sinteticas reportadas, pero aun NO implementa verificacion
visual por IA, autenticacion real ni admision al banco.

#### Etapa 3: determinar y comprobar la respuesta

El solucionario es **opcional**. Si se aporta, el sistema debe verificar su
asociacion con el ensayo y con cada pregunta y comprobar que su alternativa
existe en la version verificada. Un solucionario asociado no prueba por si
solo que una mini explicacion generada sea correcta; discrepancias o
asociaciones dudosas se registran y bloquean la confirmacion automatica.

Sin solucionario, agentes en contextos independientes resuelven las
preguntas y se contrasta su resultado mediante una comprobacion independiente.
Dos agentes que coinciden no demuestran necesariamente correccion: si falta
evidencia, hay contradicciones o no se acredita la respuesta, queda
**provisional / pendiente** y no se publica como respuesta confirmada.
Se genera una mini explicacion cuya coherencia con el procedimiento y la
respuesta tambien debe revisarse. El mecanismo exacto para validar
matematicamente y el tratamiento de casos sin pauta se ensayaran antes de
definir su automatizacion.

### 4. Salida `final.json` y PAESSED Web

La **salida objetivo de la skill** es `final.json` mas los recursos visuales
que necesite. Los campos siguientes son requisitos funcionales, NO un
JSON Schema aprobado:

- Identidad del ensayo, version/hash y procedencia.
- Por pregunta: numero/identificador; enunciado en bloques ordenados
  (texto, matematicas, imagenes, tablas); alternativas con bloques mixtos.
- Referencias a imagenes y manifiesto de recursos del paquete.
- Respuesta correcta, **solo con estado de validacion explicito**; origen
  (solucionario asociado o resolucion), o ausencia si aun no se acredita.
- Mini explicacion y su propio estado de revision.
- Referencias a la revision de fidelidad y a las incidencias relevantes.
- Metadatos educativos (eje, tema, habilidad, dificultad), cuando se
  definan y verifiquen.

El importador de PAESSED Web valida el archivo y los recursos y los renderiza
de forma segura. La interfaz no debe equiparar una respuesta propuesta con
una confirmada, ni asumir permiso de redistribucion por poder importar.

**"Preguntar a la IA":** al pulsarlo, se prepara el enunciado, alternativas,
formulas e imagenes pertinentes para una conversacion tutorial mas extensa.
La decision entre chat integrado y redireccion a un proveedor externo, asi
como el envio automatico de imagenes, sigue pendiente de viabilidad tecnica.
Nunca se deben enviar PDFs privados o datos personales sin informar al
usuario y obtener la autorizacion correspondiente.

**Compatibilidad documental pendiente:** documentos antiguos de Scanner y
Verificador nombran `exam.json` como exportacion para ensayos externos.
Este diseño acuerda `final.json` como salida objetivo de la skill; antes
de implementar la importacion hay que decidir si `exam.json` se elimina,
se convierte o queda como formato externo distinto. No se cambia
retroactivamente ningun contrato por esta seccion.

### 5. Importacion privada frente a admision al banco publico

- **Ensayo personal:** el estudiante importa el paquete y PAESSED valida
  esquema, referencias, recursos y estados; puede utilizarlo privadamente
  respetando la procedencia y advirtiendo o restringiendo respuestas no
  verificadas. Importar no concede permiso para distribuir el ensayo.
- **Banco publico:** una barrera cerrada por defecto exige aprobaciones
  validas de fidelidad, contenido educativo y derechos para el uso preciso,
  todas vinculadas a la version y evidencia concretas. Cambios o revocaciones
  invalidan la admision. Esta barrera aun NO esta implementada.

### 6. Estado y decisiones por cerrar

| Componente | Estado |
| --- | --- |
| Etapa 1, draft v1, assets, evidence, IA bajo demanda | Implementado; limites de fidelidad conocidos |
| Prototipo privado del contrato de Etapa 2 | Reportado: 37/37 pruebas sinteticas, sin integracion |
| Orquestacion de subagentes en AGY y revision visual | Por implementar |
| Agentes de resolucion, pauta opcional y mini explicaciones | Por implementar |
| `final.json` formal, paquete de imagenes, importador web y chat | Por definir/implementar |
| Barrera de admision al banco publico | Propuesta; no implementada |

**Pendientes de diseño/prueba:** elegir mecanismo de sesiones aisladas de
AGY; cantidad de lotes en paralelo; politica concreta de escalamiento y
control de tokens; validacion matematica sin solucionario; esquema versionado
de `final.json` y empaquetado de imagenes; `exam.json` heredado; modalidad
del chat; permisos de contenido; autenticacion/aprobaciones para el banco.

Los documentos `DECISIONS.md` y `technical/PAES_SCANNER.md` conservan el
historial de decisiones y el diseño original del Scanner. Esta seccion
aclara el objetivo actual sin afirmar que sus piezas pendientes ya funcionen.
