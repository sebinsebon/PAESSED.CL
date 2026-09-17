# Recuperacion de AI-on-demand — 2026-09-17

Estado recuperado: **NO INICIADA, segun la evidencia persistida**.
Estado al finalizar esta recuperacion: **COMPLETADA la validacion end-to-end**,
no la reconstruccion completa de las cinco preguntas parciales.

## Cronologia del checkpoint

1. **Sesion original congelada:** **NO INICIADA** segun la evidencia persistida;
   no dejo requests, respuestas, aplicaciones ni cambios de codigo atribuibles.
2. **Sesion de recuperacion:** ejecuto el flujo sobre los 18 candidatos reales,
   genero sus crops/requests/respuestas, aplico 6 reemplazos y 12 retenciones y
   realizo las correcciones genericas documentadas abajo.
3. **Review posterior:** AGY2 y AGY3 revisaron ese trabajo ya ejecutado y
   detectaron los defectos adicionales corregidos en la revision formal final.

## Evidencia previa a cualquier modificacion

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

## Cambios locales que ya existian

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

## Trabajo realizado durante esta recuperacion

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

## Antes y despues por pregunta

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

## Todos los candidatos probados

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

## Bugs encontrados y correcciones

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

## Verificacion final

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

## Siguiente cuello de botella real

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

## Artefactos locales de esta recuperacion

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

## Revision formal posterior del checkpoint (2026-09-17)

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
