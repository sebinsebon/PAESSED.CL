# Historial técnico del importador — septiembre de 2026

**Archivo histórico, no guía de ejecución ni estado actual.** Las fechas,
conteos y expresiones como «pendiente» pertenecen a cada evaluación. El estado
vigente está en [IMPORTADOR.md](../IMPORTADOR.md); las reglas actuales del
contrato están en [DRAFT_V1_CONTRACT.md](../DRAFT_V1_CONTRACT.md).

Esta consolidación conserva los informes y anexos que estaban repartidos entre
Arquitectura, Scanner y JSON Schema. Las rutas antiguas de artefactos que aparecen
en el texto son referencias históricas, no comandos para volver a ejecutar.

## Evolución de arquitectura — 16 y 17 de septiembre

### Refactorización genérica de cobertura — 2026-09-16

La ruta evaluada asigna identificadores deterministas a los objetos de texto y PDF (page:text:index y page:object:index). source_objects conserva región, propietario (stem, option:A... o cell:*), tipo de candidato y bbox. Los bloques tipados incluyen source_ids; las opciones conservan la referencia de su etiqueta.

La cobertura se valida por referencias de objetos, no por coincidencia de cadenas LaTeX. Un objeto sin consumidor genera un bloque unresolved y deja la pregunta en partial; un objeto consumido más de una vez genera incidencia bloqueante. La validación recorre también bloques anidados de tablas.

La detección genérica actual reconoce fracciones y raíces mediante relaciones geométricas, exponentes por desplazamiento tipográfico, ecuaciones en una línea, cuadrículas vectoriales normalizadas y asociaciones visuales solo cuando son espaciales y no ambiguas. Los reconstructores antiguos permanecen únicamente como oracle de comparación: la ejecución del importador usa una sola ruta genérica y no omite coverage.

El benchmark de desarrollo genérico queda en 5 complete y 3 partial (P9, P16, P38); run-holdout-regression-v3 queda en 7 complete y 1 partial (P35). Las parciales conservan evidencia y objetos pendientes. No se procesa holdout-v2 ni el ensayo completo hasta resolver la reconstrucción vectorial restante y revisar la fidelidad matemática de los outputs.

#### Refactorizacion generica y cobertura por objetos - 2026-09-16

La ruta evaluada de Etapa 1 es unica: inventario posicional, detectores genericos por geometria, reconstructores tipados, cobertura y draft.json. Cada objeto relevante recibe un id estable y conserva owner, candidate_type, representation y consumers. Los bloques y celdas referencian source_ids; la cobertura rechaza objetos sin consumidor, consumo duplicado o propietario incorrecto. Un candidato detectado que no puede reconstruirse queda unresolved y fuerza partial.

Las tablas solo se aceptan cuando la grilla esta demostrada; sus celdas se procesan con la misma ruta generica, de modo que la matematica interna no desaparezca. La asociacion de opciones es exclusiva y una asociacion ambigua no se resuelve por proximidad silenciosa. Los reconstructores historicos de las preguntas de desarrollo quedan solo como oracle de comparacion.

Resultado historico, anterior al control de fidelidad: run-generic-v1 tiene 7 complete y 1 partial (P38); run-holdout-regression-v3 tiene 7 complete y 1 partial (P35). Estos estados no certifican fidelidad semantica y quedan superados por la revision siguiente. Los artefactos originales se conservan.

#### Control de fidelidad estructural - 2026-09-16

La ruta generica valida propuestas tipadas antes del estado final: posiciona fracciones por baseline inline, separa texto por objetos de origen y agrupa candidatos matematicos conectados por geometria. No basta ordenar por el borde superior del numerador. Los operadores textuales, exponentes separados, agrupaciones sin transcripcion y sistemas sin evidencia suficiente impiden complete.

Solo se compone un numero mixto cuando entero y fraccion cumplen la relacion geometrica implementada. Otras expresiones conectadas no demostradas se conservan completas como candidatos unresolved, con propuestas y evidencia disponibles para AI-on-demand. Los limites geometricos son heuristicas conservadoras, no una prueba universal de correccion matematica. La deteccion actual puede sobredetectar y todavia requiere auditoria manual.

El control final recorre tablas/celdas y comprueba orden por propietario, tipo de representacion y membresia de source_ids. Las propuestas dentro de candidate_blocks son evidencia, no consumidores adicionales. Los objetos matematicos reciben candidate_id estable a partir de sus source_ids. Los reconstructores oracle siguen fuera de la ruta evaluada.

Resultados y limites actuales: [STRUCTURAL_FIDELITY_REVIEW](IMPORTADOR_2026-09.md).

#### Aritmetica simple y AI-on-demand - 2026-09-17

La deteccion determinista admite un subconjunto deliberadamente pequeno: runs contiguos de tokens numericos y operadores, literales negativos en opciones y ecuaciones inline simples. Los spans textuales que contienen una ecuacion obvia se dividen en subitems con parent_id/source_span, conservando extraction.raw.json con la salida original. No se resuelven valores.

Cada unresolved con bbox genera evidencia crop minima `reason=ai_on_demand`. `ai_on_demand.py request` entrega al CLI anfitrion solo esa ruta, el propietario, IDs de origen y una instruccion por tipo. `apply` exige respuesta estricta, valida asociacion y procedencia, registra la intervencion y vuelve a ejecutar coverage/fidelity/status. El resultado de IA se marca provisionalmente como pendiente de revalidacion; no puede elevar status por si mismo.



## Evolución del Scanner — 16 de septiembre

### Implementación inicial de Etapa 1 — 2026-09-16

Se creo la estructura inicial `skills/paes-importer/` con los casos de las ocho preguntas del benchmark, contrato local de `draft.json` y un pipeline ejecutable. La primera ejecucion produjo ocho preguntas parciales, siete paginas renderizadas y ocho incidencias `MISSING_OPTIONS`. La segmentacion fina, matematica y assets de figuras quedan pendientes de revision manual contra los PDFs. No se procesaran ensayos completos ni se implementara Etapa 2.


#### Segmentacion posicional validada - 2026-09-16

La extraccion posicional se integro con pdf-inspector 1.20.0. pypdf quedo fuera del pipeline benchmark: pdf-inspector entrega texto con x/y/width/height y PDFium aporta bounds de objetos para calcular la region vertical y el crop. Q1-Q4 de 2026 quedaron separados por marcador de pregunta, con cuatro alternativas detectadas y crops no globales. Figuras, tablas y matematica siguen pendientes; los visuales se conservan como unresolved y no se generan assets en esta prueba.


#### Assets elementales y matematica parcial - 2026-09-16

Se mantiene el crop completo de cada pregunta bajo evidence/ para auditoria. Los assets se limitan a subregiones visuales necesarias para reconstruir la pregunta: la boleta de Q2 como fallback rendered_slice con incidencia TABLE_VISUAL_FALLBACK, y el grafico del enunciado mas las cuatro alternativas visuales de Q3. Q4 incorpora expresiones completas como bloques math atomicos; las formulas inline ambiguas permanecen en texto hasta una revision posterior.

#### Reconstruccion semantica Q3-Q4 - 2026-09-16

Q3 y Q4 del benchmark 2026 se reconstruyen con bloques atomicos y ordenados por flujo inline. Las fracciones se expresan con fraccion completa, agrupando numerador y denominador sin resolver ni simplificar. Q3 conserva sus fracciones y productos como math, sin dejar tokens fragmentados en text. El grafico del enunciado y las cuatro alternativas visuales siguen siendo assets; el crop completo permanece en evidence.

La validez sintactica de LaTeX no basta para cerrar una pregunta: Q3 y Q4 mantienen needs_manual_audit=true. Se agregaron tests que rechazan el cambio semantico de convertir el numerador completo de Q4 en una resta con fraccion parcial. No se amplia el procesamiento a Q5, Q9, Q16 ni Q38 en esta iteracion.

#### Estados y presentacion matematica - 2026-09-16

El importador deriva extraction_status de incidencias y contenido pendiente: Q1, Q2, Q3 y Q4 del conjunto actual quedan complete; Q2 usa un fallback visual fiel y conserva una incidencia TABLE_VISUAL_FALLBACK no bloqueante. needs_manual_audit no se infiere solo desde ese estado.

display sigue la posicion original: la expresion inicial de Q4 y las operaciones citadas dentro de oraciones son inline (false); las fracciones de resultados mostradas en lineas independientes son display (true). No se alteran formulas, signos ni assets.

#### Benchmark restante 2027 - 2026-09-16

Se incorporaron solo P5, P9, P16 y P38. P5 conserva la barra como asset visual; P9 reconstruye su tabla vectorial con la celda 1/2 y ecuaciones monetarias inline; P16 reconstruye su tabla y asocia cuatro graficos a A-D; P38 reconstruye p=g*m, las unidades m/s2 como fraccion y el grafico del enunciado mas cuatro alternativas visuales.

Las alternativas visuales de dos columnas se ordenan por fila y columna con tolerancia a diferencias subpixel de PDF. El benchmark completo de ocho preguntas queda con 16 assets, ocho evidencias y solo la incidencia TABLE_VISUAL_FALLBACK no bloqueante de Q2. No se procesa el ensayo completo de 65 preguntas.

#### Fallback visual completo - 2026-09-16

La boleta de Q2 conserva todo el contenido necesario en un asset PNG fiel. Como no falta contenido, el estado de la pregunta es complete; la incidencia TABLE_VISUAL_FALLBACK documenta que no se pudo garantizar una tabla estructurada y usa blocks_completion=false. Las incidencias unresolved mantienen blocks_completion=true y dejan la pregunta partial.


## Anexos del contrato conceptual previo a v1

### Distinción entre evidence y assets — 2026-09-16

evidence conserva regiones de pregunta completa y sus crops para auditoria. assets contiene solamente slices visuales referenciados por bloques image; no se debe usar el crop completo de una pregunta como asset del banco. Un fallback visual fiel se registra con resolution=fallback_visual y blocks_completion=false; no convierte una pregunta completa en partial. unresolved y las incidencias con blocks_completion=true quedan reservados para contenido faltante, ilegible, ambiguo o no asociado.

#### Orden y fidelidad matematica del benchmark - 2026-09-16

Los bloques de stem preservan el orden de lectura y la posicion inline: text, math, text cuando la expresion aparece dentro de una frase. Para una barra de fraccion, numerator y denominator deben permanecer dentro del mismo bloque math y no se permite sustituir una fraccion global por una fraccion parcial. Q3 y Q4 usan esta regla en el benchmark; no se evaluan ni simplifican expresiones. Una pregunta puede conservar needs_manual_audit=true aunque el LaTeX sea sintacticamente valido.

#### Estados de extraccion y display - 2026-09-16

extraction_status describe la cobertura del contenido, no la revision posterior: complete significa que la pregunta tiene contenido utilizable, no tiene bloques unresolved y no tiene incidencias bloqueantes dirigidas a ella; partial indica contenido pendiente o una incidencia con blocks_completion=true; failed indica que no se obtuvo contenido utilizable. needs_manual_audit es independiente y puede ser true con extraction_status complete.

En bloques math, display=true se reserva para expresiones presentadas como bloque independiente en el PDF. Una expresion incrustada en una oracion usa display=false, aunque contenga una fraccion grande.

#### Benchmark 2027: tablas, visuales y math inline - 2026-09-16

Las tablas vectoriales fiables de P9 y P16 se representan como table con rows, cells y blocks; la fraccion 1/2 de P9 permanece como math inline dentro de su celda. Las ecuaciones monetarias y las unidades de P38 permanecen como math display=false dentro del texto. Los graficos de P5, P16 y P38 se conservan como assets de subregion y las alternativas los referencian individualmente. No se agregan respuestas ni clasificacion.

#### Fallback visual y recorte de alternativas - 2026-09-16

Una tabla o boleta puede quedar completa mediante un PNG fiel cuando su reconstruccion estructurada no sea confiable. La incidencia usa code=TABLE_VISUAL_FALLBACK, resolution=fallback_visual y blocks_completion=false. P16 usa crops de grafico con padding horizontal cero para excluir A/B/C/D; esas etiquetas pertenecen a options y no al asset.

#### Inventario de objetos de origen - 2026-09-16

 draft.json puede incluir source_objects, un inventario por objeto con id, region_id, owner, kind, candidate_type y bbox. Los bloques y opciones pueden incluir source_ids. La cobertura se calcula con esas referencias, incluyendo tablas y celdas anidadas; un candidato no reconstruible se conserva como unresolved y no como texto ordinario.

#### Cobertura por objetos y consumidores - 2026-09-16

source_objects registra por objeto de origen id, region_id, owner, kind, candidate_type, bbox, representation y consumers. Los bloques y opciones pueden incluir source_ids; las tablas propagan la procedencia de sus celdas y bloques anidados. La cobertura debe detectar consumo duplicado, propietario incorrecto y objetos sin consumidor. Un objeto candidato no reconstruible se conserva como unresolved, nunca se degrada silenciosamente a text.

La ruta de produccion evaluada es unica para todas las preguntas. Los reconstructores historicos de benchmark no son handlers de produccion. complete exige cobertura estructural satisfactoria; un fallback o una auditoria visual no implica partial si el contenido esta completamente representado, mientras que un unresolved real si la bloquea.

#### Fidelidad estructural adicional a cobertura - 2026-09-16

complete exige tambien structural_fidelity.complete=true. Cada bloque conserva structural_fidelity con status (verified/unresolved), reasons, source_ids, representation_type, baseline, bbox_ll y method. bbox_ll es geometria interna en puntos PDF con origen inferior izquierdo, no reemplaza las coordenadas superiores izquierdas del contrato regions. verified significa que pasa las comprobaciones implementadas, no auditoria humana ni demostracion universal de fidelidad.

Si las relaciones matematicas no se demuestran, se emite un bloque unresolved con reason=structural_fidelity_unproven, candidate_type=math, candidate_id, source_ids, evidence_id, candidate_blocks y ai_on_demand (status=pending, task=transcribe_expression_and_relations). candidate_blocks conserva propuestas para diagnostico; NO son bloques finales ni consumidores adicionales. El candidato mantiene un unico consumidor por objeto.

La incidencia STRUCTURAL_FIDELITY_UNPROVEN bloquea completitud. La validez sintactica de LaTeX, cobertura por objeto o propuestas atomicas separadas no sustituyen orden, tipo y agrupacion. needs_manual_audit permanece independiente. ai_on_demand pendiente no implica una intervencion ejecutada ni un envio al proveedor.

#### AI-on-demand - 2026-09-17

`schema/ai-response.schema.json` define la respuesta estricta del CLI anfitrion: schema_version 1.0, candidate_id, action, agent.cli/model y un unico resultado `math`, `image`, `table` o `unresolved`. No acepta campos de respuesta, solucion, explicacion, clasificacion ni confianza. El aplicador exige que result.source_ids y owner coincidan exactamente con el candidato.

Los candidatos exponen `ai_evidence_id` hacia un crop minimo en evidence. `extraction.ai_interventions` registra id, cli, model, target_id, question_id, candidate_type, evidence_ids, source_ids, action, result_type, validacion y timestamp. Aplicar una respuesta no establece extraction_status: recalcula cobertura y fidelidad; la revalidacion pendiente es bloqueante y conserva partial cuando no existe prueba estructural suficiente.


## Informe de fidelidad estructural

### Revision de fidelidad estructural generica

Fecha: 2026-09-16. Solo desarrollo y regresion existente; sin holdout-v2 ni ensayo completo.

#### Resultados de la ruta generica

| Conjunto | Complete | Partial | Assets | Crops evidence |
| --- | ---: | ---: | ---: | ---: |
| run-generic-fidelity-v1 | 3 | 5 | 16 | 8 |
| run-holdout-regression-v4 | 6 | 2 | 5 | 8 |

Desarrollo complete: 2026 P2, 2027 P5/P16. Partial: 2026 P1/P3/P4, 2027 P9/P38.
Regresion complete: 2026 P10/P20/P55, 2027 P12/P25/P60. Partial: 2026 P35, 2027 P45.

| Caso revisado | Resultado |
| --- | --- |
| 2026 P20 | text -> math -> text, formula inline preservada; complete |
| 2026 P3 | 5/6 y numero mixto 1 1/6 en orden; expresion final en un candidato atomico pendiente; partial |
| 2026 P4 | Formulas inline reordenadas; dos grupos mixtos texto/matematica sin relacion demostrada quedan pendientes; partial |
| 2027 P9 | Ecuaciones monetarias dejan de contar como texto completo: candidatos pendientes; tabla y fraccion de celda conservadas; partial |
| 2027 P45 | Fracciones, exponente y glifos de agrupacion sin transcripcion reunidos como candidato pendiente; no se afirma reconstruccion exacta; partial |

P1 tambien deja de ser complete: la expresion aritmetica y alternativas negativas estaban representadas como texto. No se introducen excepciones por numero de pregunta.

#### Cobertura y limites

No se observan consumidores duplicados. Los objetos sin consumidor se clasifican layout (264 desarrollo, 198 regresion); no son prueba de que el clasificador sea infalible. Los objetos relevantes tienen representacion o unresolved: 74 objetos consumidos por unresolved en desarrollo y 40 en regresion. Incluyen los 2 objetos previamente sin reconstruccion de P38 y los 3 de P35.

La fidelidad depende de senales y relaciones geometricas implementadas. No es una garantia universal sobre expresiones nuevas. Los grupos dudosos pueden incluir texto introductorio del mismo objeto PDF; se conserva en candidate_blocks y evidence, no se descarta. AI-on-demand queda pendiente, sin llamadas automaticas.

#### Verificacion

44 tests pasan. Trece tests de integracion ejecutan el CLI actual y leen drafts nuevos: nueve de fidelidad y cuatro de regresion. Los otros tests, incluidos oracle historicos, no se presentan como evidencia de fidelidad de la ruta generica. Las regresiones aceptan reconstruccion exacta o candidato atomico unresolved/partial donde no hay demostracion. Se incluyen mutaciones de draft para rechazar reordenamiento, degradacion math a text y promocion de P45 basada solo en coverage.

run-holdout-v1 y holdout-cases.json permanecen intactos. SHA256 originales verificados:

- draft.json: 00d2ebf4b767151fa105faa0b3313fbc5756e92e8e499a9b57ea38fa1e03b50e
- holdout-cases.json: b0258312c315a902cb259d607d83479a399f6ec15394ee917af3f48449605656

Los resultados previos run-generic-v1 y run-holdout-regression-v3 no se sobrescriben. Ver [ARQUITECTURA](../IMPORTADOR.md), [JSON_SCHEMA](../DRAFT_V1_CONTRACT.md) y [DECISIONS](../DECISIONS.md).

#### Incremento posterior: aritmetica simple y AI-on-demand

El 2026-09-17 se anadio solamente aritmetica numerica inline y ecuaciones simples. Desarrollo queda con 5 complete y 3 partial; regresion con 6 complete y 2 partial. P1 pasa a math sin resolver; P9 pasa a tres ecuaciones math inline sin resolverlas. Los casos complejos siguen bloqueados conservadoramente.

Los unresolved ahora tienen crops minimos `reason=ai_on_demand`. El flujo de host CLI usa `ai_on_demand.py` y el schema estricto; no existen adaptadores de agentes. La aplicacion registra la intervencion y fuerza revalidacion, manteniendo partial si la estructura no puede demostrarse.


## Informe de recuperación AI-on-demand

### Recuperacion de AI-on-demand — 2026-09-17

Estado recuperado: **NO INICIADA, segun la evidencia persistida**.
Estado al finalizar esta recuperacion: **COMPLETADA la validacion end-to-end**,
no la reconstruccion completa de las cinco preguntas parciales.

#### Cronologia del checkpoint

1. **Sesion original congelada:** **NO INICIADA** segun la evidencia persistida;
   no dejo requests, respuestas, aplicaciones ni cambios de codigo atribuibles.
2. **Sesion de recuperacion:** ejecuto el flujo sobre los 18 candidatos reales,
   genero sus crops/requests/respuestas, aplico 6 reemplazos y 12 retenciones y
   realizo las correcciones genericas documentadas abajo.
3. **Review posterior:** AGY2 y AGY3 revisaron ese trabajo ya ejecutado y
   detectaron los defectos adicionales corregidos en la revision formal final.

#### Evidencia previa a cualquier modificacion

- HEAD = main = origin/main = `9ca7de84c2d44d81a727f4c2064468084149e7d2`.
- `git ls-remote origin refs/heads/main` confirmo ese mismo SHA en GitHub.
- `git rev-list --left-right --count HEAD...origin/main`: `0 0`.
- `git log --oneline --decorate -10`: solo `9ca7de8` y `f9f9e7d`.
- `git diff --cached`: vacio. Ningun commit posterior al checkpoint.
- `ai_on_demand.py`, scripts, tests, fixtures y schemas eran identicos a HEAD.
- Ningun archivo inspeccionado del proyecto, incluidos runs ignorados y caches
  Python, tenia mtime posterior al commit (2026-09-17 12:41:24 -03:00).
  Se excluyeron del recorrido Git y el entorno virtual.
- No habia requests ni respuestas guardadas. Los 23 drafts historicos tenian
  cero `extraction.ai_interventions`. No aparecieron directorios temporales
  `paes-*` en el TEMP consultado.
- Los runs mas recientes eran `run-generic-ai-v1` (12:24:39, 5 complete / 3 partial)
  y `run-holdout-regression-v5` (12:24:44, 6 complete / 2 partial).
- Los nombres historicos `run-full-*` contienen ocho preguntas, no 65.
  `run-holdout-regression-v2` es una regresion historica, no holdout-v2.

Esto descarta EN PROGRESO o COMPLETADA como estados demostrados por archivos.
No permite afirmar que la sesion congelada no inspeccionara nada ni ejecutara
comandos sin persistir resultados. No hay evidencia para atribuirle tests,
requests, aplicaciones AI, cambios de codigo, nuevos tests o un run interrumpido.
Los 52 tests del checkpoint se ejecutaron durante **esta recuperacion** y pasaron.

#### Cambios locales que ya existian

Se conservaron estos 15 documentos modificados respecto de HEAD:

- `!HOME.md`
- `INBOX.md`
- `PROJECT_CONTEXT.md`
- `README.md`
- `ROADMAP.md`
- `docs/DATA_AND_CONTENT_POLICY.md`
- `product/APRENDER.md`
- `product/INICIO.md`
- `product/PLAYGROUND.md`
- `product/VERIFICADOR_PAES.md`
- `system/BANCO_PREGUNTAS.md`
- `system/ESTADISTICAS.md`
- `system/ESTRUCTURA_M1.md`
- `system/SISTEMA_ADAPTATIVO.md`
- `technical/PAES_SCANNER.md`

Tambien existia `Pasted image 20260916233735.png` sin seguimiento, ademas de
Obsidian, entorno virtual, caches y los runs ignorados. Los documentos y la
imagen ya tenian fechas anteriores al checkpoint; no se atribuyen a la sesion
congelada. Ninguno fue sobrescrito por esta recuperacion.

Inventario inicial de 477 archivos con SHA-256, mtime y estado Git:
`skills/paes-importer/benchmark/run-recovery-20260917/initial-inventory.json`.
La comprobacion final encontro un cambio concurrente en `.obsidian/workspace.json`;
ningun comando de recuperacion escribio ese archivo. No se revirtio.

#### Trabajo realizado durante esta recuperacion

1. Inspeccion de Git, documentacion, scripts, tests, schemas, runs y temporales.
2. Ejecucion de los 52 tests existentes.
3. Reproduccion y correccion generica de los defectos descritos abajo.
4. Nuevos outputs aislados de desarrollo y regresion de holdout-v1.
5. Inspeccion visual de los 18 crops minimos, sin resolver preguntas.
6. Generacion de 18 requests y 18 respuestas del CLI anfitrion Codex / GPT-6.
7. Ejecucion de 36 comandos CLI request/apply con retorno cero; seis reemplazos
   matematicos y doce retenciones explicitas, con una intervencion por candidato.
8. Comprobacion en cada paso de schema, fuentes, propietarios, ausencia de
   duplicados, estabilidad del enunciado/alternativas y bloques ajenos, historial
   de intervenciones, coverage, fidelity, partial y verification_status=not_run.
9. Suite final y controles negativos/integridad.

Se modificaron tres scripts: `ai_on_demand.py`, `import_benchmark.py` y
`structural_fidelity.py`; se actualizo el schema Python/JSON de AI-on-demand,
se ampliaron `test_generic_draft_fidelity.py`, `test_ai_on_demand.py` y
`test_holdout_regression.py`, y se agrego `tests/test_ai_apply_integrity.py`.
No se modificaron fixtures previos. Este informe y el run de recuperacion son
nuevos.

#### Antes y despues por pregunta

| Pregunta | Unresolved antes → despues | Resultado AI | Coverage despues | Estado antes → despues |
|---|---:|---|---|---|
| 2026 P3 | 1 → 0 | Expresion completa transcrita | true | partial → partial |
| 2026 P4 | 2 → 2 | Retener: prosa y formulas mezcladas | false | partial → partial |
| 2027 P38 | 5 → 5 | Retener: formula cortada, prosa/unidades y trazos aislados | false | partial → partial |
| 2026 P35 | 5 → 3 | Dos ecuaciones transcritas; tres trazos retenidos | false | partial → partial |
| 2027 P45 | 5 → 2 | Formula y alternativas A/B transcritas; C/D recortadas | false | partial → partial |

La fidelidad permanece false en las cinco preguntas. P3 demuestra que coverage
true no fuerza complete. Las seis transcripciones llevan
`ai_response_requires_revalidation`; no existe todavia una prueba independiente
que cierre sus relaciones matematicas.

Desarrollo permanece **5 complete / 3 partial**; regresion de holdout-v1,
**6 complete / 2 partial**. Las otras once preguntas no fueron alteradas por apply.

#### Todos los candidatos probados

Todos parten de unresolved. `math` significa transcripcion aplicada con fidelidad
pendiente; `unresolved` significa respuesta `retain_unresolved` registrada.

| Pregunta / owner | candidate_id | Despues / motivo |
|---|---|---|
| P3 / stem | math-82c600e850f64a0f | math; expresion agrupada visible |
| P4 / stem | math-b4e9d4c29753c0b9 | unresolved; prosa y expresiones separadas |
| P4 / stem | math-45e9365aec01fb0f | unresolved; prosa y expresiones separadas |
| P38 / stem | math-b6a1ea7703ade3bd | unresolved; operando fuera del crop |
| P38 / stem | math-1741076bbc47454f | unresolved; prosa/unidad y barra separada |
| P38 / stem | math-8453ea587e755c23 | unresolved; prosa/unidad y barra separada |
| P38 / stem | candidate-f0082695164f862b | unresolved; trazo aislado |
| P38 / stem | candidate-bc8eaba501836b64 | unresolved; trazo aislado |
| P35 / stem | math-d8ea2e1170021d52 | math; primera ecuacion visible |
| P35 / stem | math-bcd2db29f9449552 | math; segunda ecuacion visible |
| P35 / stem | candidate-7b882b6e9281e61f | unresolved; trazo vertical sin asociacion probada |
| P35 / stem | candidate-79bd3b8d329bab0b | unresolved; trazo vertical sin asociacion probada |
| P35 / stem | candidate-29aff8ba93628292 | unresolved; trazo horizontal sin asociacion probada |
| P45 / stem | math-1353dc6035953e2d | math; formula con fracciones y exponente |
| P45 / option:A | math-7711f0554c7b42ec | math; valor y unidad visibles |
| P45 / option:B | math-406b3c5aa2f0084e | math; valor y unidad visibles |
| P45 / option:C | math-87128ef0108e102e | unresolved; valor truncado a la izquierda |
| P45 / option:D | math-5e17bb7bec2a3bdf | unresolved; valor truncado a la izquierda |

#### Bugs encontrados y correcciones

- **Aliasing del enunciado:** `blocks = question['stem']; blocks.extend(...)`
  agregaba alternativas al enunciado. Ademas, reemplazar un candidato top-level
  de alternativa cambiaba esa copia agregada y dejaba intacta la alternativa real.
  Se recorren ahora los contenedores originales por separado, incluida recursion
  existente para tablas. Las regresiones verifican aislamiento y consumo unico.
- **Crops omitidos:** se generaban antes de los unresolved descubiertos por
  coverage. Se generan despues de completar ese inventario. Los cinco candidatos
  de objetos aislados reciben ahora evidencia minima propia.
- **Fallback silencioso:** request aceptaba evidencia de la pregunta completa
  cuando faltaba ai_evidence_id. Ahora falla explicitamente en ese caso.
- **Incidencias eliminadas prematuramente:** aplicar un candidato eliminaba
  pendientes de toda la pregunta. Se conservan mientras queden unresolved y
  se actualizan los fallos de fidelidad desde el nuevo informe.
- **Geometria ausente:** un candidato sin baseline/bbox podia producir KeyError
  al aplicar una respuesta. Ahora se registra missing_source_geometry y partial.
- **Motivo de retencion perdido:** la intervencion no guardaba la respuesta ni
  su reason. Ahora conserva la respuesta estructurada completa para auditoria.

Las regresiones nuevas fallaron contra el comportamiento anterior y pasaron tras
las correcciones. La prueba de crops se amplio a alternativas y exige evidencia
ai_on_demand del candidato, detectando los cinco crops ausentes.

#### Verificacion final

- `.paes-importer-venv/Scripts/python.exe -B -m unittest discover -s tests -v`:
  **63/63**, OK. La suite dirigida de integridad/recovery queda en **21/21**.
- `git diff --check`: sin errores; solo avisos de normalizacion CRLF/LF.
- 18 respuestas validan tambien contra el schema publicado. El contrato Python
  y el schema coinciden descontando metadatos `$schema` y `title`.
- Cinco respuestas invalidas fueron rechazadas sin escribir output: complete
  impuesto, answer adicional, propietario distinto, fuente distinta y candidato
  inexistente.
- 21 assets verificados por SHA-256; 34 evidencias existentes con bbox dentro
  de pagina; 18 hashes de crops registrados en results.json.
- Ningun run historico ni documento preexistente cambio de hash.
- SHA-256 de run-holdout-v1/draft.json:
  `00d2ebf4b767151fa105faa0b3313fbc5756e92e8e499a9b57ea38fa1e03b50e`.
- SHA-256 de holdout-cases.json:
  `b0258312c315a902cb259d607d83479a399f6ec15394ee917af3f48449605656`.
- No se ejecuto holdout-v2 ni el ensayo de 65 preguntas. No hubo commit ni push.

#### Siguiente cuello de botella real

La unidad de candidato y la prueba de fidelidad posterior a IA. Hay candidatos
que agrupan prosa con varias formulas, otros que separan una barra de su fraccion
y bounds de texto que cortan digitos u operandos. El contrato actual reemplaza un
solo bloque; no puede reconstruir fielmente una secuencia mixta ni demostrar la
asociacion de trazos aislados. Hace falta mejorar esas fronteras y la evidencia
local antes de ampliar el benchmark.

Incluso una transcripcion legible como P3 permanece pendiente: fidelity_report
comprueba metadatos y orden, pero no demuestra por si mismo las relaciones de una
formula nueva aportada por IA. No se introdujo una aprobacion artificial ni
excepciones para preguntas concretas.

#### Artefactos locales de esta recuperacion

Todo bajo `skills/paes-importer/benchmark/run-recovery-20260917/`, ignorado por Git:

- `initial-inventory.json`: frontera entre estado previo y recuperacion.
- `development/` y `holdout-v1-regression/`: draft inicial, assets y evidence.
- `*.request.json` y `*.response.json`: solicitudes y respuestas por candidato.
- `applied-NN.json`: estado despues de cada aplicacion.
- `after-ai.json`: estado final de cada conjunto con coverage/fidelity/status.
- `results.json`: antes/despues detallado de los 18 candidatos y hashes de crops.
- `commands.json`: los 36 comandos positivos y sus retornos.
- `*.invalid.json` y `verification.json`: controles negativos e integridad final.
- `exercise.py`: runner de evidencia; las transcripciones especificas viven solo
  aqui, nunca como excepciones en el importador.

#### Revision formal posterior del checkpoint (2026-09-17)

Despues de la recuperacion, AGY2 (arquitectura) y AGY3 (revision critica) inspeccionaron de forma
independiente el diff completo desde `9ca7de8`, el schema, los tests, los
artefactos y este documento. Ambos rechazaron el checkpoint inicial por fallos
reales y coincidentes: incidencias estructurales obsoletas despues de aplicar
una respuesta, geometria perdida en candidatos creados por coverage y un
schema de tablas que aceptaba filas malformadas. AGY2 ademas detecto que
`baseline: null` podia romper fidelity; AGY3 detecto el mismo borde y confirmó
que el issue de retencion se duplicaba al reintentar.

Se corrigieron solo esos fallos del checkpoint: el recálculo elimina y vuelve a
derivar las incidencias generadas de coverage/fidelity/unresolved; los
candidatos de coverage conservan `bbox_ll`, `baseline` y `source_ids`; la
respuesta de tabla exige filas, celdas y bloques de tipos validos; `baseline` nulo
se trata como geometria ausente; y la incidencia AI de retencion usa un codigo
propio y upsert estable por `candidate_id`. Se agregaron regresiones para cada
caso. Las observaciones sobre padding de crops, candidatos sin geometria, tests
legacy y duplicacion de schema quedan como riesgos o mejoras futuras porque no
permiten completar de forma segura.

La suite completa pasa 63/63 y el ejercicio de recovery vuelve a producir 18
candidatos: 6 `replace`, 12 `retain_unresolved`; las 18 preguntas siguen
`partial`, aunque una alcanza `coverage.complete=true`, y las 18 mantienen
`structural_fidelity.complete=false`. No se ejecutaron holdout-v2 ni las 65
preguntas. El checkpoint de código está listo para una revisión de commit
selectivo; el workspace completo sigue mezclado con documentación e imagen
preexistentes y no debe confirmarse con `git add .`.


## Fuentes y resultados registrados al 23 de septiembre



Se inspeccionaron estos PDFs locales, ambos M1, Forma 111, 57 paginas y 65 preguntas:

- `Ensayos\PAES-INVIERNO-M1 2026.pdf` — SHA-256 `A93B574DE086266CF62CD23202BB2385794D38F6EBF4E85E4FA02EA876587973`.
- `Ensayos\2027-26-06-17-paes-invierno-oficial-matematica1-p2027.pdf` — SHA-256 `8034742BBA71F899661187813CE6E1EFB820097024899C0879541B0E7A1974E3`.

Benchmark inicial, usando pagina del archivo base 1:

- 2026: preguntas 1 y 2, pagina 3; pregunta 3, pagina 4; pregunta 4, pagina 5.
- 2027: pregunta 5, pagina 6; pregunta 9, pagina 9; pregunta 16, pagina 14; pregunta 38, pagina 31.

La muestra cubre texto, signos, moneda, formulas, fracciones, figura geometrica, tabla, graficos y alternativas visuales. No se fabricara un caso multipagina si no aparece en estos PDFs; se validara cuando exista uno real.

#### Resultados registrados de Etapa 1

Los artefactos de benchmark existentes contienen estas muestras de ocho preguntas. Los conteos corresponden a `extraction_status` (`complete` / `partial`):

| Muestra | Complete | Partial |
| --- | ---: | ---: |
| Development | 5 | 3 |
| Holdout-v1 | 6 | 2 |
| Holdout-v2 / Ensayo 326 | 1 | 7 |
| Tesla | 0 | 8 |
| Matematica (1) | 1 | 7 |

Holdout-v2 fue una primera ejecucion parcial de ocho preguntas de Ensayo 326, cuyo ensayo completo tiene 65 preguntas. En la corrida registrada de Matematica (1), Q10 quedo `partial` y Q19 `complete`. El checkpoint Q10/Q19 se cerro en `4c244a0`, publicado en `origin/main`; la suite paso 111/111 al cierre.
