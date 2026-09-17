# Arquitectura

## Proposito

Definir Etapa 1 del importador: reconstruir ensayo PDF en borrador estructurado y trazable. No define Etapa 2 ni Scanner.

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
