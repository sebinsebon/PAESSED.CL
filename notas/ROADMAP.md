# Roadmap

Este es el orden principal para definir, construir y validar PAESSED. Las pruebas se realizan durante cada fase, no solamente al final.

## Foco actual del importador

La referencia única de estado es [IMPORTADOR](../docs/IMPORTADOR.md).
Las fases de este roadmap describen el producto; no son las etapas 1/2/3 del pipeline.

- [x] Implementar productor y validador draft v1 y las abstenciones publicadas.
- [x] Validar privadamente estructura e integridad del contrato de revisión (37 pruebas sintéticas archivadas).
- [x] Confirmar manualmente una respuesta sintética nueva de AGY2.
- [ ] Ejecutar y evaluar las pruebas sintéticas preparadas de aislamiento y lectura visual.
- [ ] Preparar un piloto acotado de revisión de fidelidad, sin resolver preguntas.
- [ ] Integrar revisión, propuestas y aprobación de versiones exactas.
- [ ] Acreditar selección y procesamiento de un ensayo completo.
- [ ] Desarrollar respuestas comprobadas, mini explicaciones, final.json y su importación web.

## Fase 0 - Alcance del MVP

- [x] Definir idea general
- [x] Separar Inicio / Aprender / Playground / Verificador
- [x] Concepto inicial de PAES Scanner
- [x] Crear base open source inicial
- [x] Definir politica inicial de datos y contenido
- [x] Agregar archivos base para GitHub y contribuciones
- [x] Definir a que estudiante ayudara primero y cual es su problema principal
- [x] Definir el recorrido minimo: diagnostico -> resumen -> practica guiada -> explicacion -> progreso -> siguiente actividad
- [x] Decidir que incluye y que no incluye la primera version
- [x] Escribir criterios de aceptacion para el recorrido principal
- [x] Definir como se evaluara el piloto con estudiantes

El MVP ayudara a estudiantes con base debil y a estudiantes con buena base que quieran acercarse a 1000 puntos. El problema principal es detectar brechas y convertirlas en una nivelacion y una siguiente actividad claras.

El recorrido minimo sera:

1. Test diagnostico corto dentro de la web.
2. Resumen porcentual de fortalezas y debilidades por eje y habilidad.
3. Nivelacion y practica guiada.
4. Explicacion, progreso y siguiente actividad recomendada.
5. Ensayo PAES completo opcional dentro de la web para recalibrar el perfil sin borrar el progreso anterior.

El primer MVP tambien incluira PAES Scanner y Verificador para ensayos externos. Los resultados importados podran recalibrar el perfil, pero el usuario podra corregir errores de lectura antes de confirmarlos. Playground y Ranking apareceran como Proximamente. El MVP sera gratuito y no incluira pagos ni publicidad.

El recorrido principal se considerara comprensible cuando un estudiante pueda completar el test corto, entender su principal debilidad, iniciar la nivelacion y reconocer cual es su siguiente leccion mediante las indicaciones de la interfaz.

El piloto comenzara con 5 estudiantes reales de confianza. Se observara si completan el recorrido principal, donde se confunden, que errores encuentran y si comprenden sus resultados y siguiente leccion. Si el recorrido funciona sin bloqueos graves, el piloto se ampliara a mas estudiantes.

**Resultado esperado:** una descripcion breve y comprobable de la primera version.

## Fase 1 - Fundamentos educativos y contenido

- [x] Investigar y validar la estructura curricular oficial de M1
- [x] Definir una taxonomia inicial de ejes, temas, habilidades y prerrequisitos
- [ ] Definir una muestra pequena de contenido para el MVP
- [x] Definir campos, procedencia, revision y versionado de las preguntas
- [ ] Revisar las condiciones de uso del contenido antes de publicarlo
- [ ] Seleccionar y validar el contenido del diagnóstico inicial de 12 preguntas ya acordado
- [ ] Definir el ensayo PAES completo y como recalibra el perfil
- [ ] Definir una primera regla de dominio simple y explicable
- [ ] Definir que ocurre con aciertos, errores, omisiones y preguntas repetidas
- [ ] Definir como las correcciones confirmadas del Verificador recalibran el perfil
- [ ] Definir practica diaria, avance, dificultad y repaso de prerrequisitos
- [ ] Escribir casos de ejemplo para comprobar las reglas adaptativas

**Resultado esperado:** las mismas respuestas producen una recomendacion consistente y se reconoce cuando no hay evidencia suficiente.

## Fase 2 - Flujo y UI/UX

- [ ] Definir arquitectura de navegacion y onboarding
- [ ] Disenar los estados del recorrido principal en Inicio y Aprender
- [ ] Disenar el aviso descartable del ensayo PAES completo en Inicio
- [ ] Disenar el flujo Scanner -> revision -> correccion -> confirmacion -> Verificador
- [ ] Incluir estados sin datos, carga, error, interrupcion y regreso
- [ ] Crear bocetos para movil y escritorio
- [ ] Revisar la paleta, logos y referencia existente en Stitch
- [ ] Definir sistema visual y componentes base
- [ ] Definir accesibilidad para teclado, contraste, formulas, figuras y alternativas largas
- [ ] Probar el prototipo con estudiantes antes de implementar todas las pantallas

**Resultado esperado:** un estudiante entiende que hacer, puede completar el recorrido y sabe cual es su siguiente actividad.

## Fase 3 - Tecnologia, backend y datos

- [ ] Elegir tecnologias y documentar por que se eligieron
- [ ] Definir responsabilidades del navegador, servidor y base de datos
- [ ] Evaluar Vercel y Supabase segun necesidades y presupuesto
- [ ] Modelar usuario, contenido M1, preguntas, sesiones, respuestas, historial, dominio y estadisticas
- [ ] Definir relaciones, restricciones, migraciones y versionado de datos
- [ ] Definir autenticacion y permisos para aislar los datos de cada estudiante
- [ ] Definir contratos para iniciar, responder, reanudar y cerrar una sesion
- [ ] Definir el contrato futuro de `final.json` para el banco y la web
- [x] Implementar contrato versionado y productor de `draft.json` v1 para Etapa 1; la fidelidad general sigue en validación
- [x] Implementar `draft.json` v1: esquema y validación semántica con identidad de fuentes para selecciones de uno o varios PDFs
- [x] Crear estructura minima real de `skills/paes-importer/`
- [x] Definir estructura de `assets/`, `evidence/` e incidencias
- [x] Elegir y probar `pdf-inspector` para extraccion y PDFium para renders/crops
- [x] Implementar contrato AI-on-demand con el CLI anfitrion, sin API central obligatoria
- [x] Definir la separacion entre `draft.json`, futura verificacion y posterior enriquecimiento
- [ ] Separar el contenido importado, las correcciones del usuario y los intentos confirmados
- [ ] Definir procesamiento local, limites de archivos y ciclo de vida de derivados del Scanner
- [ ] Resolver doble envio, recarga, omisiones y cambios posteriores en preguntas
- [ ] Definir datos personales minimos, secretos, logs, copias y restauracion

**Resultado esperado:** arquitectura, modelo de datos y permisos suficientemente claros para implementar sin inventarlos pantalla por pantalla.

## Fase 4 - Implementacion del MVP

- [ ] Crear el proyecto, entornos y comprobaciones automaticas basicas
- [ ] Implementar autenticacion y navegacion principal
- [ ] Crear base de datos, migraciones y permisos
- [ ] Cargar un banco piloto de preguntas revisadas
- [x] Implementar el pipeline base de Etapa 1 y ejecutar el benchmark inicial de 8 preguntas
- [x] Cerrar el registro privado de ensayos, respaldos y movimientos seguros (`8e3579a`)
- [ ] Cerrar los criterios de aceptación de Etapa 1 y su validación de ensayo completo; contrato y productor v1 ya implementados, con defectos de fidelidad conocidos
- [ ] Implementar pregunta -> respuesta -> explicacion -> historial
- [ ] Implementar diagnostico, resumen y seleccion de siguiente practica
- [ ] Implementar ensayo PAES completo opcional y recalibracion del perfil
- [ ] Implementar PAES Scanner y Verificador con correccion antes de confirmar resultados
- [ ] Implementar progreso y estadisticas iniciales sin falsa precision
- [ ] Implementar estados vacios, carga, error y reanudacion
- [ ] Probar reglas educativas, persistencia y recorrido completo durante la implementacion
- [ ] Comprobar con dos usuarios que no puedan acceder a datos ajenos
- [ ] Comprobar que recargas y reintentos no dupliquen el progreso

Las muestras y el cierre más reciente están en [Validación registrada](../docs/IMPORTADOR.md#validación-registrada). No equivalen a ensayos completos ni a revisión visual exhaustiva.

**Resultado esperado:** un estudiante completa el ciclo, regresa y conserva correctamente su avance.

## Fase 5 - Piloto y ajustes

- [ ] Probar el MVP con un grupo pequeno de estudiantes
- [ ] Registrar errores, dudas y puntos donde no saben continuar
- [ ] Revisar claridad de explicaciones, recomendaciones y estadisticas
- [ ] Ajustar UI/UX y sistema adaptativo segun evidencia
- [ ] Comprobar despliegue, copias y restauracion
- [ ] Comparar los resultados con los criterios definidos en la fase 0
- [ ] Decidir que funcionalidad merece construirse despues

**Resultado esperado:** una decision basada en el uso real sobre que corregir o ampliar.

## Fase 6 - Expansiones posteriores

### Playground

- [ ] Definir filtros, historial, preguntas falladas y modo aleatorio
- [ ] Definir como sus resultados afectan dominio y estadisticas

### Ranking

- [ ] Definir practica diaria competitiva separada de ensayos editables
- [ ] Definir puntuacion, ligas, empates, temporadas y controles de integridad

### Pagos

- [ ] Decidir si existira una oferta pagada y que valor entregara, sin asumir derechos comerciales sobre contenido de terceros

### Senales metacognitivas

- [ ] Probar una accion opcional para marcar una pregunta como dificil, desconocida o respondida con duda
- [ ] Validar si esta senal ayuda a detectar aciertos por azar sin introducir friccion ni sesgos
- [ ] Decidir su peso en el dominio solamente despues de medirla

Estas senales no forman parte del primer MVP.
