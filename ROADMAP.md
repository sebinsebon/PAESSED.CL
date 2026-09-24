# Roadmap

Este es el orden principal para definir, construir y validar PAESSED. Las pruebas se realizan durante cada fase, no solamente al final.

## Fase 0 - Alcance del MVP

- [x] Definir idea general
- [x] Separar Inicio / Aprender / Playground / Verificador
- [x] Concepto inicial de PAES Scanner
- [x] Crear base open source inicial
- [x] Definir politica inicial de datos y contenido
- [x] Agregar archivos base para GitHub y contribuciones
- [ ] Definir a que estudiante ayudara primero y cual es su problema principal
- [ ] Definir el recorrido minimo: diagnostico -> resumen -> practica guiada -> explicacion -> progreso -> siguiente actividad
- [ ] Decidir que incluye y que no incluye la primera version
- [ ] Escribir criterios de aceptacion para el recorrido principal
- [ ] Definir como se evaluara el piloto con estudiantes

La propuesta actual es dejar Playground avanzado, Verificador, Scanner, prediccion de puntaje, rankings y pagos fuera del primer MVP. Debe confirmarse antes de registrarlo en [[DECISIONS]].

**Resultado esperado:** una descripcion breve y comprobable de la primera version.

## Fase 1 - Fundamentos educativos y contenido

- [ ] Investigar y validar la estructura curricular oficial de M1
- [ ] Definir una taxonomia inicial de ejes, temas, habilidades y prerrequisitos
- [ ] Definir una muestra pequena de contenido para el MVP
- [ ] Definir campos, procedencia, revision y versionado de las preguntas
- [ ] Revisar las condiciones de uso del contenido antes de publicarlo
- [ ] Definir el diagnostico inicial
- [ ] Definir una primera regla de dominio simple y explicable
- [ ] Definir que ocurre con aciertos, errores, omisiones y preguntas repetidas
- [ ] Definir practica diaria, avance, dificultad y repaso de prerrequisitos
- [ ] Escribir casos de ejemplo para comprobar las reglas adaptativas

**Resultado esperado:** las mismas respuestas producen una recomendacion consistente y se reconoce cuando no hay evidencia suficiente.

## Fase 2 - Flujo y UI/UX

- [ ] Definir arquitectura de navegacion y onboarding
- [ ] Disenar los estados del recorrido principal en Inicio y Aprender
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
- [ ] Resolver doble envio, recarga, omisiones y cambios posteriores en preguntas
- [ ] Definir datos personales minimos, secretos, logs, copias y restauracion

**Resultado esperado:** arquitectura, modelo de datos y permisos suficientemente claros para implementar sin inventarlos pantalla por pantalla.

## Fase 4 - Implementacion del MVP

- [ ] Crear el proyecto, entornos y comprobaciones automaticas basicas
- [ ] Implementar autenticacion y navegacion principal
- [ ] Crear base de datos, migraciones y permisos
- [ ] Cargar un banco piloto de preguntas revisadas
- [x] Implementar el pipeline base de Etapa 1 y ejecutar el benchmark inicial de 8 preguntas
- [ ] Estabilizar y validar Etapa 1; el contrato versionado de `draft.json` sigue pendiente y nuevos holdouts pueden revelar problemas de generalizacion
- [ ] Implementar pregunta -> respuesta -> explicacion -> historial
- [ ] Implementar diagnostico, resumen y seleccion de siguiente practica
- [ ] Implementar progreso y estadisticas iniciales sin falsa precision
- [ ] Implementar estados vacios, carga, error y reanudacion
- [ ] Probar reglas educativas, persistencia y recorrido completo durante la implementacion
- [ ] Comprobar con dos usuarios que no puedan acceder a datos ajenos
- [ ] Comprobar que recargas y reintentos no dupliquen el progreso

Los resultados de las muestras de ocho preguntas estan en [[PROJECT_CONTEXT#Resultados registrados de Etapa 1]]. Holdout-v2 cubrio parcialmente Ensayo 326; el checkpoint Q10/Q19 quedo cerrado en `4c244a0`.

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

### Verificador PAES

- [ ] Completar y versionar el contrato exam.json
- [ ] Definir importacion, validaciones, privacidad y visualizacion
- [ ] Definir como los ensayos importados afectan estadisticas

### PAES Scanner

- [ ] Extraccion fisica desde PDF
- [ ] Segmentacion de paginas y preguntas
- [ ] Resolucion de preguntas en grupos pequenos
- [ ] Validacion y reprocesamiento de errores concretos
- [ ] Merge final y exportacion a exam.json
- [ ] Pruebas con documentos permitidos y distintos formatos
