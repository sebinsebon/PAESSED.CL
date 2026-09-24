# Project Context

## Objetivo

Crear una plataforma de preparacion para PAES M1 que detecte fortalezas y debilidades y adapte automaticamente el aprendizaje del estudiante.

El proyecto se puede nombrar provisionalmente como "Proyecto PAES M1". El nombre comercial definitivo esta por definir.

## Idea central

Diagnostico
-> perfil de dominio
-> ruta personalizada
-> practica
-> nuevos resultados
-> actualizacion del perfil
-> nueva adaptacion.

## Areas

1. [[product/INICIO]]: dashboard personal del estudiante, con progreso, fortalezas, debilidades, recomendaciones y orientacion inicial.
2. [[product/APRENDER]]: experiencia guiada de aprendizaje, organizada como ruta adaptable por eje, tema, habilidad y leccion.
3. [[product/PLAYGROUND]]: practica libre donde el usuario decide que quiere ejercitar usando filtros y preguntas oficiales disponibles.
4. [[product/VERIFICADOR_PAES]]: visualizador de ensayos importados desde un archivo estructurado.
5. [[technical/PAES_SCANNER]]: importador de Etapa 1 para procesar PDFs de forma local-first.

## Principios

- Codigo abierto con bases claras de colaboracion.
- Personalizacion.
- Aprendizaje basado en debilidades.
- Sesiones manejables.
- Gamificacion que ayude y no distraiga.
- Utilizar contenido oficial DEMRE cuando corresponda.
- Local-first para contenido privado.
- Separar algoritmos deterministas de tareas apropiadas para IA.
- No depender de una API central de IA para el importador. Usar IA del CLI del propio usuario solo bajo demanda.
- Mantener separadas extraccion, verificacion y enriquecimiento.
- Disenar primero el producto antes de optimizar demasiado la arquitectura tecnica.

## Open Source

PAESSED se publicara como proyecto de codigo abierto. El repositorio debe poder
recibir colaboraciones sin comprometer privacidad, derechos de autor ni calidad
educativa.

Reglas base:

- No versionar secretos ni credenciales.
- No versionar datos reales de estudiantes.
- No versionar PDFs privados.
- No versionar preguntas, imagenes o bancos de contenido sin permiso claro.
- Mantener decisiones aceptadas en [[DECISIONS]].
- Revisar [[docs/DATA_AND_CONTENT_POLICY]] antes de agregar contenido educativo.

## Estado

El producto sigue en fase de definicion. La skill real `skills/paes-importer/` y el importador generico de Etapa 1 ya estan implementados: generan `draft.json`, `assets/`, `evidence/` e incidencias, y mantienen `partial` cuando falta fidelidad estructural. AI-on-demand funciona mediante el CLI anfitrion. La verificacion independiente de Etapa 2 y el enriquecimiento a `final.json` siguen pendientes. El Scanner de respuestas de la web, la taxonomia aplicada, la resolucion y las explicaciones pedagogicas no forman parte de esta implementacion.

## Insumos y benchmark de Etapa 1

Se inspeccionaron estos PDFs locales, ambos M1, Forma 111, 57 paginas y 65 preguntas:

- `C:\Users\Administrator\Documents\Paessed.cl\Ensayos\PAES-INVIERNO-M1 2026.pdf` — SHA-256 `A93B574DE086266CF62CD23202BB2385794D38F6EBF4E85E4FA02EA876587973`.
- `C:\Users\Administrator\Documents\Paessed.cl\Ensayos\2027-26-06-17-paes-invierno-oficial-matematica1-p2027.pdf` — SHA-256 `8034742BBA71F899661187813CE6E1EFB820097024899C0879541B0E7A1974E3`.

Benchmark inicial, usando pagina del archivo base 1:

- 2026: preguntas 1 y 2, pagina 3; pregunta 3, pagina 4; pregunta 4, pagina 5.
- 2027: pregunta 5, pagina 6; pregunta 9, pagina 9; pregunta 16, pagina 14; pregunta 38, pagina 31.

La muestra cubre texto, signos, moneda, formulas, fracciones, figura geometrica, tabla, graficos y alternativas visuales. No se fabricara un caso multipagina si no aparece en estos PDFs; se validara cuando exista uno real.

## Resultados registrados de Etapa 1

Los artefactos de benchmark existentes contienen estas muestras de ocho preguntas. Los conteos corresponden a `extraction_status` (`complete` / `partial`):

| Muestra | Complete | Partial |
| --- | ---: | ---: |
| Development | 5 | 3 |
| Holdout-v1 | 6 | 2 |
| Holdout-v2 / Ensayo 326 | 1 | 7 |
| Tesla | 0 | 8 |
| Matematica (1) | 1 | 7 |

Holdout-v2 fue una primera ejecucion parcial de ocho preguntas de Ensayo 326, cuyo ensayo completo tiene 65 preguntas. En la corrida registrada de Matematica (1), Q10 quedo `partial` y Q19 `complete`. El checkpoint Q10/Q19 se cerro en `4c244a0`, publicado en `origin/main`; la suite paso 111/111 al cierre.

No se deben tratar ideas tecnicas experimentales como decisiones definitivas si no estan registradas en [[DECISIONS]].

## Como mantener esta documentacion

- Idea rapida -> [[INBOX]]
- Tarea o fase -> [[ROADMAP]]
- Decision tomada -> [[DECISIONS]]
- Cambio fundamental de vision -> [[PROJECT_CONTEXT]]
- Funcionamiento especifico -> documento correspondiente
- Informacion vieja pero que conviene conservar -> [[archive]]
