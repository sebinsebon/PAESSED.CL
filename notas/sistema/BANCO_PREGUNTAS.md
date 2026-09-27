# Banco de Preguntas

## Proposito

Definir como incorporar preguntas clasificadas para diagnostico, ensayo completo, Aprender, estadisticas y futuras expansiones sin mezclar extraccion automatica, revision educativa y permiso de publicacion.

Estado: requisitos y propuesta del banco; la barrera de admisión aún no está implementada.

## Flujo acordado

PDF o publicacion oficial
-> Analizador de Ensayos local
-> `draft.json` -> revisión de fidelidad (`verified.json`)
-> respuestas y explicaciones (`final.json`, contrato pendiente)
-> revision humana
-> validacion estructural y curricular
-> validacion de derechos
-> importacion al banco canonico

El JSON por ensayo es un artefacto de importacion revisable. No es la fuente final de la aplicacion. El banco canonico permitira deduplicar, buscar, corregir y versionar preguntas de varios ensayos.

## Identidad del ensayo

No se debe usar solamente "PAES 2027", porque puede confundirse el ano de aplicacion con el proceso de admision.

Cada ensayo debe registrar:

- institucion y prueba;
- ano de aplicacion;
- proceso de admision;
- temporada: regular o invierno;
- forma, si se conoce;
- publicacion completa o seleccion de preguntas;
- URL oficial;
- hash SHA-256 del documento fuente;
- fecha de obtencion.

Ejemplo: **PAES de Invierno aplicada en 2026, Proceso de Admision 2027**.

## Campos minimos por pregunta

- ID canonico y version.
- Numero original y pagina de origen.
- Bloques ordenados de texto, formula e imagen.
- Alternativas completas, incluyendo assets cuando corresponda.
- Clave correcta y procedencia de la clave.
- Explicacion breve, autor y procedencia: oficial, propia, comunitaria o asistida por IA.
- Version curricular usada para clasificar.
- Eje, unidad, habilidad primaria y habilidad secundaria opcional.
- Dificultad y procedencia de esa estimacion.
- Estado de puntuacion: puntuada, piloto, anulada o desconocida.
- Estado de revision de extraccion, clave, taxonomia y explicacion.
- Estado de distribucion y fundamento del permiso.

La IA puede proponer una explicacion o clasificacion, pero no debe convertirlas automaticamente en verdad canonica. La clave correcta debe contrastarse con el clavijero oficial cuando exista.

## Imagenes y formulas

- No guardar imagenes grandes como Base64 dentro del JSON.
- Guardar assets separados, identificados por hash y referenciados mediante una ruta.
- Registrar texto alternativo para accesibilidad.
- Conservar fórmulas revisadas en LaTeX. La elección del renderizador web (MathJax o KaTeX) sigue pendiente de unificación; no cambia el contrato de extracción.
- Si el OCR matematico es ambiguo, conservar temporalmente un recorte visual y marcar la pregunta para revision.

## Derechos y publicacion

El sitio de DEMRE indica que sus contenidos son propiedad de la institucion y la normativa de las pruebas restringe su reproduccion. La publicacion de un PDF no demuestra por si sola permiso para copiarlo a una aplicacion o repositorio.

Algunos modelos historicos contienen condiciones de uso educativo no comercial con atribucion. Esa condicion debe comprobarse documento por documento; no se puede extender automaticamente a todos los ensayos ni a todos los anos.

Estados obligatorios:

- `private_local`: procesado localmente, no distribuible por el proyecto.
- `curated_review`: revisado tecnicamente, pero sin permiso de publicacion confirmado.
- `public_authorized`: existe fundamento verificable para mostrarlo publicamente.

Solo `public_authorized` puede llegar al banco servido por la aplicacion. Mantener JSON y assets fuera de GitHub no basta si el servidor igualmente muestra contenido sin autorizacion.

Fuentes de referencia:

- Publicaciones oficiales: https://portaldemre.demre.cl/publicaciones/
- Seleccion y pruebas publicadas: https://portaldemre.demre.cl/publicaciones/2025/pruebas-oficiales-y-seleccion-preguntas-paes-p2025
- Derechos y deberes: https://portaldemre.demre.cl/paes/normativa/derechos-deberes-postulante

## Contenido open source

El repositorio puede incluir:

- Analizador de Ensayos y validadores.
- Contratos y schemas.
- Fixtures sinteticos.
- Taxonomia y herramientas de importacion.

No debe incluir sin permiso verificable:

- PDFs oficiales o privados.
- JSON con preguntas copiadas.
- Imagenes extraidas.
- Claves, explicaciones o derivados protegidos.

## Pendientes

- [ ] Obtener una respuesta o autorizacion verificable de DEMRE para el uso previsto.
- [x] Definir campos, procedencia, revision y versionado inicial.
- [ ] Definir validaciones deterministas del banco.
- [ ] Definir deteccion de duplicados y preguntas repetidas.
- [ ] Definir muestra pequena de contenido sintetico o autorizado para el MVP.
- [ ] Validar clasificaciones historicas contra el temario M1 vigente.

## Relacion con producto

- [[producto/APRENDER]] usa preguntas publicables para lecciones y practica.
- [[producto/PLAYGROUND]] usara el banco para practica libre cuando se implemente.
- [[sistema/ESTADISTICAS]] usa eje, unidad y habilidad para recalibrar el perfil.
- [PAES_SCANNER](../../docs/IMPORTADOR.md) genera el artefacto de importacion.
- [Contrato draft v1](../../docs/DRAFT_V1_CONTRACT.md) define el borrador; el contrato de `final.json` y el modelo del banco siguen pendientes.
