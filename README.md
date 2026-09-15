# PAESSED

PAESSED es una plataforma abierta de preparacion para PAES Matematica M1.
El objetivo es ayudar a estudiantes a detectar fortalezas y debilidades,
practicar con foco y avanzar por una ruta de aprendizaje adaptativa.

El proyecto esta en fase temprana de definicion y diseno. La prioridad actual
es construir buenas bases de producto, contenido, datos y colaboracion antes de
implementar grandes partes del sistema.

## Vision

La idea central del producto es:

```text
diagnostico
-> perfil de dominio
-> ruta personalizada
-> practica
-> nuevos resultados
-> actualizacion del perfil
-> nueva adaptacion
```

El sistema debe reconocer que habilidades domina el estudiante, que habilidades
necesita reforzar y que actividad conviene hacer despues.

## Areas del Producto

- `Inicio`: dashboard personal con progreso, fortalezas, debilidades y siguiente actividad recomendada.
- `Aprender`: ruta guiada y adaptable por eje, tema, habilidad y leccion.
- `Playground`: practica libre filtrable para que el estudiante elija que ejercitar.
- `Verificador PAES`: visualizador de ensayos importados desde un archivo estructurado.
- `PAES Scanner`: herramienta complementaria, local-first, para convertir PDFs permitidos en `exam.json`.

## Estado Actual

El repositorio contiene principalmente documentacion de producto y arquitectura:

- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md): vision general y principios.
- [`ROADMAP.md`](ROADMAP.md): fases y prioridades.
- [`DECISIONS.md`](DECISIONS.md): decisiones ya aceptadas.
- [`product/`](product/): especificaciones de areas del producto.
- [`system/`](system/): sistema adaptativo, estadisticas, banco de preguntas y estructura M1.
- [`technical/`](technical/): arquitectura, contrato JSON y PAES Scanner.
- [`design/`](design/): criterios UI/UX y referencias.

## Principios

- Personalizacion real, no solo progreso cosmetico.
- Aprendizaje basado en debilidades accionables.
- Sesiones manejables para estudiantes.
- Gamificacion que ayude a estudiar y no distraiga.
- Uso responsable de contenido oficial o autorizado.
- Procesamiento local-first para contenido privado.
- Separacion entre reglas deterministas y tareas apropiadas para IA.
- Cuidado con metricas que puedan dar falsa precision.

## Contenido y Datos

No subas al repositorio:

- PDFs privados de ensayos.
- Bancos de preguntas sin permiso de uso o redistribucion.
- Datos personales de estudiantes.
- Respuestas, historiales, logs o exports reales de usuarios.
- Secretos, tokens, credenciales o llaves API.

Lee [`docs/DATA_AND_CONTENT_POLICY.md`](docs/DATA_AND_CONTENT_POLICY.md) antes de agregar contenido educativo, datasets o ejemplos.

## Como Contribuir

Las contribuciones son bienvenidas, pero el proyecto aun esta definiendo sus bases.
Antes de abrir cambios grandes, revisa:

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`docs/OPEN_SOURCE_GUARDRAILS.md`](docs/OPEN_SOURCE_GUARDRAILS.md)
- [`DECISIONS.md`](DECISIONS.md)

Las ideas exploratorias deben vivir primero en `INBOX.md` o en documentos de diseno.
Las decisiones aceptadas deben quedar registradas en `DECISIONS.md`.

## Licencia

El codigo y la documentacion del repositorio se publican bajo la licencia MIT.
Revisa [`LICENSE`](LICENSE) para mas detalles.

La licencia del repositorio no entrega permisos sobre materiales de terceros,
como preguntas oficiales, ensayos privados, PDFs o imagenes externas.
