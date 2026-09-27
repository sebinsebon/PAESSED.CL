# Contrato de `draft.json` v1 — Etapa 1

Estado: esquema, validador y productor v1 implementados.
`import_benchmark.py` emite `1.0.0` mediante `draft_v1_emitter.py`.
Los baselines antiguos no se convierten ni reemplazan por este cambio documental.

Referencia general: [Importador](IMPORTADOR.md). Contrato ejecutable:
[draft.v1.schema.json](../skills/paes-importer/schema/draft.v1.schema.json);
validación semántica: [draft_contract.py](../skills/paes-importer/scripts/draft_contract.py).

## Identidad y procedencia

`schema_version` es exactamente `1.0.0`. Hay un solo esquema para un PDF o un
benchmark: `sources` contiene una o más fuentes con ID, SHA-256 y número total
de páginas. `run.purpose` y `run.selection_sha256` son metadatos opcionales;
no cambian la estructura. Los IDs de fuentes son únicos dentro del draft; el
hash identifica los bytes del PDF, no su nombre ni su año. `local_path` es una
referencia local opcional y el validador no abre el PDF.

`pages` incluye solo las páginas extraídas, con `source_id` y `page_number`
físico, basado en 1. Dos PDFs pueden tener la misma página 1, pero cada página
tiene un `id` único. `regions.page_id` apunta a esa página y `questions.region_ids`
es una lista ordenada: una pregunta puede ocupar varias páginas del mismo PDF.
Un contexto compartido puede tener sus propias regiones y ser referenciado
por varias preguntas del mismo PDF. Una pregunta que mezcla PDFs distintos se
rechaza en v1; si aparece un anexo externo, habrá que definir explícitamente
su semántica antes de permitirlo.
Si una pregunta es `complete`, cada contexto referenciado también debe tener
bloques estructuralmente verificados y cobertura propia de sus objetos.

Las coordenadas de `regions.bbox` usan puntos PDF del marco visible orientado,
origen superior izquierdo. `source_objects.bbox` y las pruebas `bbox_ll` de
fidelidad conservan su geometría interna con origen inferior izquierdo. No se
convierten silenciosamente. El validador tolera hasta 0,5 puntos de redondeo
en el borde de una región, sin recortarla.

## Contenido preservado

El esquema tipa bloques `text`, `math`, `image`, `table` y `unresolved`, con
tablas recursivas. Conserva `source_objects`, `source_ids`, `owner`,
`structural_fidelity`, `candidate_id`, `candidate_type`, `candidate_blocks`,
`ai_evidence_id` y `ai_on_demand`. `candidate_blocks` son propuestas de
auditoría y no consumen objetos de origen adicionales. Registra incidencias,
`blocks_completion`, `resolution`, fallos estructurales, assets, evidence y
`extraction.ai_interventions`, incluida la respuesta original del CLI. Los
campos futuros solo pueden entrar en `extensions` con claves nombradas como
`vendor.campo`; no se descartan campos desconocidos para obtener un v1 válido.

`evidence` y `assets` tienen rutas relativas y SHA-256. La comprobación de
archivos es optativa para permitir CI sin materiales privados. Si se activa,
verifica bytes, rechaza rutas que escapen de sus carpetas y no sigue enlaces
simbólicos. `sources[].local_path` no participa en esa comprobación.

## Semántica de estados

`complete` describe únicamente la extracción estructural de una pregunta.
Exige bloques utilizables, ausencia de `unresolved` e incidencias bloqueantes,
cobertura única de los objetos de origen con propietario correcto y fidelidad
estructural recalculada sobre los bloques. `needs_manual_audit` puede seguir
siendo `true`. `partial` conserva contenido e incertidumbre; `failed` no tiene
bloques utilizables. El estado global resume los estados de las preguntas.

No hay campo de respuesta correcta, solucionario, explicación, clasificación
ni dificultad. La existencia de un solucionario no interviene en la validación
de `complete`. `verification_status` permanece `not_run`: la revisión
independiente de fidelidad pertenece a Etapa 2 y las respuestas a Etapa 3.

## Compatibilidad y límites

`draft_contract.read_draft` lee `0.1.0` sin escribir ni intentar certificarlo
como v1. Valida `1.0.0` con JSON Schema 2020-12 y reglas semánticas. El
esquema `draft.schema.json` legado permanece intacto. No hay conversión
automática: el mapa histórico `document.sha256/page_count` por año no basta
si faltan correspondencias inequívocas con páginas y objetos. Una conversión
futura debe producir otro archivo y registrar cualquier dato no demostrable,
sin inventarlo ni sobreescribir baselines.

La recomputación de fidelidad usa la geometría y pruebas guardadas en el
draft. No puede demostrar que el extractor detectó todos los objetos del PDF:
esa limitación requiere auditoría visual y nuevos holdouts. Los contextos y
fragmentos tienen una estructura mínima en v1; sus semánticas compartidas
necesitan más casos reales antes de ampliar el contrato. La respuesta
AI-on-demand embebida se valida con su esquema actual `1.0`, separado de la
versión del draft.

## Productor actual

El productor emite `sources[]`, asocia páginas a sus fuentes, añade hashes a
las evidencias, completa los campos de incidencias y deriva el estado global.
Ensambla y valida v1 en un directorio temporal antes de publicar la salida.
Mantiene los baselines históricos; no es un conversor automático de borradores
legados. Las selecciones y los manifiestos privados siguen separados del código.

## Representación y revisión

Los enunciados y alternativas son listas ordenadas de bloques mixtos. `math`
contiene LaTeX sin `$`; `display` distingue fórmulas independientes de inline.
`image` referencia un asset, mientras que `evidence` conserva material de auditoría.
Un fallback visual fiel puede ser no bloqueante; contenido faltante, ambiguo o
mal asociado debe permanecer pendiente. Los objetos no pueden consumirse dos
veces ni atribuirse a un propietario distinto para aparentar cobertura.

Los `candidate_blocks` conservan propuestas, no contenido final adicional.
Las relaciones no demostradas pueden envolverse como `unresolved`, preservando
IDs, texto o LaTeX, propietario, motivos y evidencia. `verified` significa que
pasan los controles internos implementados: no prueba fidelidad visual universal.

El contrato de [respuesta AI-on-demand](../skills/paes-importer/schema/ai-response.schema.json)
permanece separado. Exige candidato, acción, agente y resultado tipado, sin
respuestas educativas ni confianza usada como aprobación. El aplicador verifica
procedencia y propietario exactos, conserva la respuesta y recalcula los estados.
Ni una respuesta de IA ni la existencia de este esquema autorizan una pregunta
para el banco público. `verified.json` y `final.json` pertenecen a otros alcances.
