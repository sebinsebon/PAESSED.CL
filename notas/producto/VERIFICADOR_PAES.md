# Verificador PAES — producto web

Estado: especificación de producto; implementación pendiente. Este Verificador
muestra ensayos y resultados del estudiante. La **revisión de fidelidad de
Etapa 2** es un proceso técnico diferente, explicado en
[Pipeline del importador](../../docs/IMPORTADOR.md). El formato objetivo de importación es `final.json`;
su contrato todavía no está implementado. Importar un ensayo privado no lo
publica en el banco.

## Proposito

Verificador PAES permite analizar ensayos que el estudiante ya realizo, usando un archivo estructurado importado en la web.

## Experiencia del usuario

La web recibira posteriormente contenido verificado. Durante el desarrollo de la Etapa 1, el artefacto intermedio se llama `draft.json` y puede contener incidencias o bloques `unresolved`.

La web deberia mostrar:

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

El [contrato draft v1](../../docs/DRAFT_V1_CONTRACT.md) y su productor están implementados. El [pipeline del importador](../../docs/IMPORTADOR.md) describe sus límites. Respuestas, explicaciones, taxonomía, estadísticas e importación web pertenecen a etapas posteriores; no forman parte del borrador.

Antes de confirmar una importacion, el usuario podra corregir respuestas, metadatos o contenido cuando el Scanner haya leido algo de forma incorrecta o una pregunta sea defectuosa. Solo los resultados confirmados recalibraran el perfil de dominio y las recomendaciones.

Las correcciones del Verificador no otorgaran puntos en el futuro modo Ranking. Ranking usara solamente preguntas diarias controladas por el sistema.

La condición de contenido oficial no sustituye la revisión de permisos. La admisión pública exige fidelidad, revisión educativa y derechos; importar para uso privado es un flujo diferente.

Para ensayos externos, el enfoque sera local-first: el servidor de la plataforma no deberia almacenar PDFs privados originales.

## Preguntas abiertas

- Como se ingresaran las respuestas del estudiante?
- Que validaciones debe hacer la web al importar contenido verificado?
- Como se mostraran y conservaran las correcciones antes de confirmar el ensayo?
- Como se revierte una confirmacion incorrecta sin perder trazabilidad?
- Como manejar imagenes muy pesadas dentro del JSON?

## Pendientes

- [ ] Definir visualizacion de grilla.
- [ ] Definir vista por pregunta.
- [ ] Definir importacion de contenido verificado (`final.json`).
- [ ] Definir relacion con estadisticas.
- [ ] Definir limites de privacidad y almacenamiento.
