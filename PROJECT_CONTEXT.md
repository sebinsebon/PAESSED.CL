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
5. [[technical/PAES_SCANNER]]: herramienta complementaria y separada para procesar PDFs privados de forma local-first.

## Principios

- Codigo abierto con bases claras de colaboracion.
- Personalizacion.
- Aprendizaje basado en debilidades.
- Sesiones manejables.
- Gamificacion que ayude y no distraiga.
- Utilizar contenido oficial DEMRE cuando corresponda.
- Local-first para contenido privado.
- Separar algoritmos deterministas de tareas apropiadas para IA.
- No depender de una API central de IA para PAES Scanner.
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
El proyecto esta actualmente en fase de definicion y diseno. La vision principal ya existe, pero la arquitectura, los algoritmos de dominio, la taxonomia curricular y varios flujos del producto todavia no estan completamente cerrados.

No se deben tratar ideas tecnicas experimentales como decisiones definitivas si no estan registradas en [[DECISIONS]].

## Como mantener esta documentacion

- Idea rapida -> [[INBOX]]
- Tarea o fase -> [[ROADMAP]]
- Decision tomada -> [[DECISIONS]]
- Cambio fundamental de vision -> [[PROJECT_CONTEXT]]
- Funcionamiento especifico -> documento correspondiente
- Informacion vieja pero que conviene conservar -> [[archive]]
