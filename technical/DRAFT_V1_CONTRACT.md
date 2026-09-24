# Contrato de `draft.json` v1 — Etapa 1

Estado: esquema y validador implementados; el importador todavía produce
`0.1.0`. Este documento no autoriza convertir ni reemplazar los baselines.

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
de `complete`. `verification_status` permanece `not_run`: verificar respuestas
es otra etapa.

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

## Adaptación futura del productor

El importador deberá emitir `sources[]`, asociar cada `page` a su fuente,
añadir SHA-256 a cada `evidence`, completar `blocks_completion` en todas las
incidencias y calcular el estado global desde los estados por pregunta. Debe
emitir los campos de procedencia y fidelidad exigidos sin alterar los drafts
históricos. La adaptación y su benchmark de regresión serán otro checkpoint;
la selección del próximo holdout virgen debe fijarse antes de ejecutarlo.
