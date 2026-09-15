# Inicio

## Proposito

Inicio es el dashboard del estudiante. Debe mostrar el estado actual de su preparacion y sugerir que hacer a continuacion.

## Experiencia del usuario

Cuando el usuario es nuevo y todavia no hay informacion suficiente, Inicio debe orientarlo a realizar un diagnostico inicial.

Cuando ya existe informacion, Inicio puede mostrar:

- progreso general;
- puntaje estimado, si se define una forma responsable de calcularlo;
- fortalezas;
- debilidades;
- dominio por eje;
- dominio por temas especificos;
- racha de estudio;
- actividad recomendada;
- practica diaria;
- evolucion del rendimiento.

## Funcionamiento actual

El funcionamiento esta en etapa conceptual. Inicio debe apoyarse en [[../system/ESTADISTICAS]] y en el perfil de dominio definido por [[../system/SISTEMA_ADAPTATIVO]].

Estados iniciales:

- Usuario sin diagnostico: mostrar orientacion y llamada a diagnostico.
- Usuario con diagnostico: mostrar resumen, debilidades prioritarias y siguiente actividad recomendada.

## Preguntas abiertas

- Que informacion debe aparecer en el primer pantallazo?
- Como evitar que el puntaje estimado parezca una promesa exacta?
- Que deberia priorizarse: progreso, debilidades o siguiente accion?
- Como mostrar fortalezas sin hacer que el usuario descuide repaso?

## Pendientes

- [ ] Definir contenido del dashboard nuevo.
- [ ] Definir contenido del dashboard con diagnostico.
- [ ] Definir formato de actividad recomendada.
- [ ] Definir reglas para mostrar racha.
- [ ] Definir si se mostrara puntaje estimado en el MVP.
