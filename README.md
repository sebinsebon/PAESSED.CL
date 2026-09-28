# PAESSED

PAESSED es un proyecto abierto para apoyar la preparación de la PAES de
Matemática 1 mediante diagnóstico, práctica guiada y seguimiento del aprendizaje.

El proyecto está en desarrollo. El repositorio contiene documentación del
producto y un importador experimental que convierte selecciones de preguntas
desde PDF en un borrador estructurado. La aplicación web todavía no está
implementada.

## Importación de ensayos

El trabajo actual se concentra en preparar preguntas con su texto, fórmulas,
alternativas, imágenes y procedencia. La primera etapa genera `draft.json`,
`assets/` y `evidence/`. Conserva los casos ambiguos como pendientes de revisión
en vez de afirmar que su reconstrucción es correcta.

El importador está en desarrollo y sus evaluaciones cubren muestras de preguntas;
no debe considerarse todavía un conversor validado para cualquier ensayo completo.
No resuelve las preguntas ni genera claves de respuesta o explicaciones.

La visión del proyecto separa tres tareas:

1. Reconstruir el contenido del PDF.
2. Revisar de forma independiente que el borrador coincida con el documento.
3. Comprobar las respuestas y preparar explicaciones para la plataforma.

Solo la primera etapa está implementada. La revisión independiente, la generación
de respuestas y explicaciones, el paquete final y la importación web siguen en
desarrollo o planificación.

## Documentación

- [Estado y arquitectura del importador](docs/IMPORTADOR.md)
- [Contrato de `draft.json` v1](docs/DRAFT_V1_CONTRACT.md)
- [Decisiones del proyecto](docs/DECISIONS.md)
- [Política de datos y contenido](docs/DATA_AND_CONTENT_POLICY.md)
- [Cómo contribuir](CONTRIBUTING.md)

## Colaboración y contenido

Se agradecen correcciones, mejoras a las herramientas, documentación y pruebas
con ejemplos sintéticos. Consulta la política de datos antes de añadir material
educativo. No incorpores PDFs privados, preguntas, imágenes o claves de terceros
sin autorización verificable, ni datos personales de estudiantes.

El código y la documentación propia se distribuyen bajo la licencia [MIT](LICENSE).
Esta licencia no otorga derechos sobre contenido de terceros usado para evaluar
el importador.
