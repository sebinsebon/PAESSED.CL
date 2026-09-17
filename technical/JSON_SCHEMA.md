# JSON Schema

## Proposito y estado

Definir contrato de `draft.json`, salida local y revisable de Etapa 1. No contiene respuestas correctas, explicaciones, eje, habilidad ni dificultad. Esos datos pertenecen a etapas posteriores.

```text
PDF -> draft.json + assets/ + evidence/
```

Contrato formal: JSON Schema 2020-12, independiente de Zod u otra libreria.

## Forma general

Objeto raiz contiene: `schema_version`; `document` con fuente, hash y paginas; `extraction` con estado, herramientas, intervenciones de IA y `verification_status`; `pages`; `regions`; `assets`; `evidence`; `contexts`; `questions`; `unassigned_fragments`; e `issues`.

## Pregunta y bloques

Cada pregunta tiene `id` estable, `original_number` como texto o `null`, `region_ids`, `context_ids`, `stem`, `options` y `extraction_status` (`complete`, `partial` o `failed`). No se asume numeracion consecutiva ni cuatro alternativas.

`stem` y cada alternativa son listas ordenadas de bloques. Tipos:

- `text`: texto literal normalizado con escape seguro.
- `math`: objeto con `latex` y `display`; sin delimitadores `$`.
- `image`: objeto con `asset_id`.
- `table`: filas y celdas, cuyos contenidos vuelven a ser bloques.
- `unresolved`: referencia a evidencia, texto bruto disponible y motivo.

Una alternativa puede mezclar texto, matematica, imagen y tabla. Un contexto compartido puede ser usado por varias preguntas.

## Procedencia y coordenadas

`pages` registra dimensiones, CropBox, rotacion y transformacion. `regions` usa pagina base 1, marco visible ya orientado, origen superior izquierdo y `[x0, y0, x1, y1]` en puntos PDF. Cada region conserva matriz usada para mapearla a pixeles.

No usar `bbox_global` para varias paginas. Pregunta multipagina referencia varias regiones ordenadas.

## Assets y evidence

`assets` registra `asset_id`, ruta relativa bajo `assets/`, MIME, dimensiones, SHA-256 y `region_ids`. Solo contiene imagenes que forman parte de pregunta.

`evidence` registra paginas o crops bajo `evidence/`, tipo, ruta, regiones y motivo (`audit`, `ambiguity`, `source`). `extraction.raw.json` puede conservar salida cruda de herramientas.

## IA e incidencias

`ai_interventions` registra CLI o proveedor, capacidad usada, objetivo, IDs de regiones enviadas, timestamp y resultado. Nunca registra secretos.

Cada incidencia es objeto con `id`, `code`, `severity`, `target_id`, `region_ids`, `evidence_ids` y `message`. Ejemplos: `AMBIGUOUS_FORMULA`, `MISSING_OPTIONS`, `COORDINATE_TRANSFORM`, `TABLE_VISUAL_FALLBACK`.

Una continuacion dudosa conserva fragmentos y puede marcar `continuation_candidate: true`; no se fusiona destructivamente.

## Estados y validaciones

Validar JSON, tipos, IDs unicos, rutas existentes, MIME, dimensiones, hashes, regiones dentro de pagina, orden de bloques y referencias. `verification_status` permanece `not_run` en toda salida de Etapa 1.

## Fuera de este contrato

Respuestas correctas, explicaciones, taxonomia, dificultad, respuestas del estudiante, derechos de publicacion y estadisticas se modelaran despues, sin alterar procedencia del borrador.


## Distincion evidence versus assets - 2026-09-16

evidence conserva regiones de pregunta completa y sus crops para auditoria. assets contiene solamente slices visuales referenciados por bloques image; no se debe usar el crop completo de una pregunta como asset del banco. Un fallback visual fiel se registra con resolution=fallback_visual y blocks_completion=false; no convierte una pregunta completa en partial. unresolved y las incidencias con blocks_completion=true quedan reservados para contenido faltante, ilegible, ambiguo o no asociado.

## Orden y fidelidad matematica del benchmark - 2026-09-16

Los bloques de stem preservan el orden de lectura y la posicion inline: text, math, text cuando la expresion aparece dentro de una frase. Para una barra de fraccion, numerator y denominator deben permanecer dentro del mismo bloque math y no se permite sustituir una fraccion global por una fraccion parcial. Q3 y Q4 usan esta regla en el benchmark; no se evaluan ni simplifican expresiones. Una pregunta puede conservar needs_manual_audit=true aunque el LaTeX sea sintacticamente valido.

## Estados de extraccion y display - 2026-09-16

extraction_status describe la cobertura del contenido, no la revision posterior: complete significa que la pregunta tiene contenido utilizable, no tiene bloques unresolved y no tiene incidencias bloqueantes dirigidas a ella; partial indica contenido pendiente o una incidencia con blocks_completion=true; failed indica que no se obtuvo contenido utilizable. needs_manual_audit es independiente y puede ser true con extraction_status complete.

En bloques math, display=true se reserva para expresiones presentadas como bloque independiente en el PDF. Una expresion incrustada en una oracion usa display=false, aunque contenga una fraccion grande.

## Benchmark 2027: tablas, visuales y math inline - 2026-09-16

Las tablas vectoriales fiables de P9 y P16 se representan como table con rows, cells y blocks; la fraccion 1/2 de P9 permanece como math inline dentro de su celda. Las ecuaciones monetarias y las unidades de P38 permanecen como math display=false dentro del texto. Los graficos de P5, P16 y P38 se conservan como assets de subregion y las alternativas los referencian individualmente. No se agregan respuestas ni clasificacion.
\n## Fallback visual y recorte de alternativas - 2026-09-16

Una tabla o boleta puede quedar completa mediante un PNG fiel cuando su reconstruccion estructurada no sea confiable. La incidencia usa code=TABLE_VISUAL_FALLBACK, resolution=fallback_visual y blocks_completion=false. P16 usa crops de grafico con padding horizontal cero para excluir A/B/C/D; esas etiquetas pertenecen a options y no al asset.

## Inventario de objetos de origen - 2026-09-16

 draft.json puede incluir source_objects, un inventario por objeto con id, region_id, owner, kind, candidate_type y bbox. Los bloques y opciones pueden incluir source_ids. La cobertura se calcula con esas referencias, incluyendo tablas y celdas anidadas; un candidato no reconstruible se conserva como unresolved y no como texto ordinario.

## Cobertura por objetos y consumidores - 2026-09-16

source_objects registra por objeto de origen id, region_id, owner, kind, candidate_type, bbox, representation y consumers. Los bloques y opciones pueden incluir source_ids; las tablas propagan la procedencia de sus celdas y bloques anidados. La cobertura debe detectar consumo duplicado, propietario incorrecto y objetos sin consumidor. Un objeto candidato no reconstruible se conserva como unresolved, nunca se degrada silenciosamente a text.

La ruta de produccion evaluada es unica para todas las preguntas. Los reconstructores historicos de benchmark no son handlers de produccion. complete exige cobertura estructural satisfactoria; un fallback o una auditoria visual no implica partial si el contenido esta completamente representado, mientras que un unresolved real si la bloquea.

## Fidelidad estructural adicional a cobertura - 2026-09-16

complete exige tambien structural_fidelity.complete=true. Cada bloque conserva structural_fidelity con status (verified/unresolved), reasons, source_ids, representation_type, baseline, bbox_ll y method. bbox_ll es geometria interna en puntos PDF con origen inferior izquierdo, no reemplaza las coordenadas superiores izquierdas del contrato regions. verified significa que pasa las comprobaciones implementadas, no auditoria humana ni demostracion universal de fidelidad.

Si las relaciones matematicas no se demuestran, se emite un bloque unresolved con reason=structural_fidelity_unproven, candidate_type=math, candidate_id, source_ids, evidence_id, candidate_blocks y ai_on_demand (status=pending, task=transcribe_expression_and_relations). candidate_blocks conserva propuestas para diagnostico; NO son bloques finales ni consumidores adicionales. El candidato mantiene un unico consumidor por objeto.

La incidencia STRUCTURAL_FIDELITY_UNPROVEN bloquea completitud. La validez sintactica de LaTeX, cobertura por objeto o propuestas atomicas separadas no sustituyen orden, tipo y agrupacion. needs_manual_audit permanece independiente. ai_on_demand pendiente no implica una intervencion ejecutada ni un envio al proveedor.

## AI-on-demand - 2026-09-17

`schema/ai-response.schema.json` define la respuesta estricta del CLI anfitrion: schema_version 1.0, candidate_id, action, agent.cli/model y un unico resultado `math`, `image`, `table` o `unresolved`. No acepta campos de respuesta, solucion, explicacion, clasificacion ni confianza. El aplicador exige que result.source_ids y owner coincidan exactamente con el candidato.

Los candidatos exponen `ai_evidence_id` hacia un crop minimo en evidence. `extraction.ai_interventions` registra id, cli, model, target_id, question_id, candidate_type, evidence_ids, source_ids, action, result_type, validacion y timestamp. Aplicar una respuesta no establece extraction_status: recalcula cobertura y fidelidad; la revalidacion pendiente es bloqueante y conserva partial cuando no existe prueba estructural suficiente.
