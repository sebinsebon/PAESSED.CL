# Verificador PAES

## Proposito

Verificador PAES permite analizar ensayos que el estudiante ya realizo, usando un archivo estructurado importado en la web.

## Experiencia del usuario

El usuario importara un archivo `exam.json`. La web deberia mostrar:

- preguntas;
- respuestas del estudiante;
- respuestas correctas;
- correctas;
- incorrectas;
- omitidas;
- explicacion;
- eje;
- tema;
- imagenes o graficos si existen.

La revision podria mostrarse como una grilla de preguntas y una vista detallada por pregunta.

## Funcionamiento actual

El contrato conceptual de importacion esta en [[../technical/JSON_SCHEMA]]. La herramienta complementaria que podria generar ese archivo es [[../technical/PAES_SCANNER]].

Hay que distinguir entre contenido DEMRE oficial que si puede formar parte directamente de la plataforma y ensayos externos o materiales protegidos.

Para ensayos externos, el enfoque sera local-first: el servidor de la plataforma no deberia almacenar PDFs privados originales.

## Preguntas abiertas

- Como se ingresaran las respuestas del estudiante?
- Que validaciones debe hacer la web al importar `exam.json`?
- Como afectaran los errores del ensayo al perfil de dominio?
- Debe permitirse editar metadatos de una pregunta importada?
- Como manejar imagenes muy pesadas dentro del JSON?

## Pendientes

- [ ] Definir visualizacion de grilla.
- [ ] Definir vista por pregunta.
- [ ] Definir importacion de `exam.json`.
- [ ] Definir relacion con estadisticas.
- [ ] Definir limites de privacidad y almacenamiento.
