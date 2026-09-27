# Sistema Adaptativo

## Proposito

Definir como el producto decide que estudiar, cuando avanzar, cuando repasar y como usar las debilidades del estudiante para personalizar la experiencia.

## Perfil de dominio

La idea base es mantener dominio por:

Eje
-> Tema
-> Habilidad

Ejemplo conceptual:

Algebra y Funciones
-> Funciones
-> Funcion cuadratica
-> dominio: 42%

La formula exacta todavia esta por definir.

## Regla provisional de ubicacion

El test diagnostico corto se evaluara por eje y habilidad, no solamente mediante un promedio global.

- Tendria 12 preguntas fijas y una duracion objetivo maxima de 15 minutos.
- Incluiria 3 preguntas por eje y 3 por habilidad primaria, cruzadas de forma equilibrada.
- Cada eje incluiria una pregunta basica, una intermedia y una avanzada.
- Al terminar se mostrarian porcentajes por eje y habilidad con la etiqueta **Resultado inicial aproximado**.
- No se bloquearian porcentajes ni se mostraria un contador de evidencias en el MVP.

- Resultado de 80% o mas en un eje o habilidad: iniciar en una ruta de repaso y recomendar el ensayo PAES completo para obtener un perfil con mas evidencia.
- Resultado menor a 80%: iniciar una ruta de nivelacion centrada en las brechas detectadas.

El 80% es un umbral inicial que debe validarse durante el piloto. No significa dominio definitivo. La practica guiada diaria, el ensayo PAES completo y los ensayos externos confirmados agregaran evidencia y podran recalibrar el perfil.

## Senales posibles

El sistema podria observar:

- respuestas correctas e incorrectas;
- omisiones;
- dificultad de la pregunta;
- tema y habilidad;
- historial reciente;
- diagnostico inicial;
- actividades guiadas;
- practica libre;
- ensayos importados.
- senales metacognitivas opcionales, como indicar que una pregunta fue dificil o se respondio con duda.

## Dificultad

La dificultad puede subir si el estudiante muestra dominio suficiente y bajar si aparecen errores persistentes. No hay una regla matematica definitiva.

## Avance

El avance puede depender de dominio por habilidad, no solo de completar lecciones. El diagnostico puede modificar el punto inicial de la ruta, segun [DECISIONS](../../docs/DECISIONS.md).

## Repaso

El sistema deberia detectar debilidades y reintroducir temas en practica diaria o actividades guiadas.

## Debilidades

Las debilidades deben ser accionables: no basta con decir que el estudiante esta bajo en un eje, tambien debe sugerirse que habilidad estudiar.

## Por definir

- Formula de dominio.
- Peso de cada tipo de actividad.
- Regla para saltar contenido.
- Regla para desbloquear dificultad mayor.
- Regla para repasar prerrequisitos.
- Relacion entre Playground y dominio.
- Relacion entre ensayos importados y dominio.

## Preguntas abiertas

- El dominio debe decaer con el tiempo?
- Como evitar que una buena racha o mala racha pequena distorsione demasiado el perfil?
- Cuantas preguntas hacen falta para confiar en una estimacion?
- Como representar incertidumbre?
- Como validar o ajustar el umbral provisional de 80%?
- Las senales de dificultad percibida mejoran la estimacion o agregan sesgo y friccion?
