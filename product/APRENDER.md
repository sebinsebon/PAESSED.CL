# Aprender

## Proposito

Aprender es la experiencia principal de estudio guiado. El sistema decide que conviene estudiar segun el avance y el perfil de dominio del estudiante.

## Experiencia del usuario

La interfaz estara inspirada en una ruta tipo Duolingo:

- unidades;
- temas;
- habilidades;
- niveles;
- lecciones;
- progreso;
- desbloqueos.

La estructura conceptual esperada es:

Eje
-> Tema
-> Habilidad
-> Leccion

El usuario no necesariamente debe comenzar desde la primera leccion. El diagnostico inicial puede permitir saltos de contenido, avance mas rapido o preguntas mas dificiles si demuestra dominio suficiente.

Si demuestra debilidad, el sistema puede reforzar contenido, bajar dificultad, mostrar prerrequisitos o hacer que el tema aparezca con mas frecuencia en practicas futuras.

## Funcionamiento actual

Aprender depende de:

- [[../system/ESTRUCTURA_M1]]
- [[../system/SISTEMA_ADAPTATIVO]]
- [[../system/BANCO_PREGUNTAS]]
- [[../system/ESTADISTICAS]]

El objetivo no es tener solo un nivel global, sino un perfil de dominio por eje, tema y habilidad.

La practica diaria deberia usar ese perfil para escoger pocas preguntas centradas especialmente en debilidades.

## Preguntas abiertas

- Como se calcula el mastery o dominio de una habilidad?
- Cuanto peso tiene una respuesta correcta reciente?
- Cuando una habilidad se considera dominada?
- Cuando puede saltarse contenido?
- Cuando debe subir o bajar la dificultad?
- Como aparecen los prerrequisitos?
- Que rol tienen XP, niveles, rachas y vidas?
- Las preguntas dificiles deberian entregar mas XP?
- Como evitar que la gamificacion distraiga del aprendizaje?

## Pendientes

- [ ] Definir taxonomia M1.
- [ ] Definir modelo de dominio por habilidad.
- [ ] Definir diagnostico inicial.
- [ ] Definir reglas de salto de contenido.
- [ ] Definir reglas de dificultad dinamica.
- [ ] Definir practica diaria.
- [ ] Definir progresion visual.
