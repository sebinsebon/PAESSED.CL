# Playground

## Proposito

Playground es practica libre. A diferencia de [[APRENDER]], aqui el usuario decide que quiere practicar.

## Experiencia del usuario

El usuario deberia poder filtrar preguntas oficiales DEMRE por:

- ano;
- eje;
- tema;
- dificultad;
- cantidad;
- preguntas no realizadas;
- preguntas falladas anteriormente.

Tambien podria existir una accion como "Sorprendeme" para generar una practica aleatoria.

## Funcionamiento actual

Playground se apoya en [[../system/BANCO_PREGUNTAS]] y puede alimentar [[../system/ESTADISTICAS]].

La relacion con el sistema de dominio todavia no esta definida. Una idea inicial es que sus resultados tengan menos peso que un diagnostico o actividades guiadas, pero esto no es una decision cerrada.

## Preguntas abiertas

- Cuanto deben influir las respuestas del Playground en el mastery score?
- Como tratar preguntas que el usuario ya vio en Aprender?
- Deben existir modos por tiempo o por cantidad?
- Como mostrar el historial sin convertirlo en una pagina pesada?
- Que significa exactamente una practica aleatoria util?

## Pendientes

- [ ] Definir filtros del MVP.
- [ ] Definir relacion con dominio.
- [ ] Definir historial de preguntas.
- [ ] Definir vista de preguntas falladas.
- [ ] Definir comportamiento de "Sorprendeme".
