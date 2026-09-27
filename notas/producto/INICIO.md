# Inicio

## Proposito

Inicio es el dashboard del estudiante. Debe mostrar el estado actual de su preparacion y sugerir que hacer a continuacion.

## Experiencia del usuario

Cuando el usuario es nuevo y todavia no hay informacion suficiente, Inicio debe orientarlo a realizar un diagnostico inicial.

El diagnostico inicial sera un test fijo de 12 preguntas dentro de la web, con una duracion objetivo maxima de 15 minutos. Debe entregar una primera ubicacion para estudiantes con base debil y para estudiantes con buena base, sin prometer precision mayor que la evidencia disponible.

La muestra se balanceara con 3 preguntas por eje y 3 por habilidad primaria. Cada eje tendra una pregunta basica, una intermedia y una avanzada.

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

El funcionamiento esta en etapa conceptual. Inicio debe apoyarse en [[sistema/ESTADISTICAS]] y en el perfil de dominio definido por [[sistema/SISTEMA_ADAPTATIVO]].

Estados iniciales:

- Usuario sin diagnostico: mostrar orientacion y llamada a diagnostico.
- Usuario con diagnostico: mostrar resumen, debilidades prioritarias y siguiente actividad recomendada.
- Usuario con diagnostico corto: mostrar un aviso superior descartable que ofrezca realizar un ensayo PAES completo dentro de la web.
- Usuario con ensayo completo: recalibrar el perfil y actualizar recomendaciones sin borrar progreso anterior.

Las fortalezas y debilidades se mostraran inmediatamente como porcentajes por eje y habilidad. Despues de las 12 preguntas llevaran la etiqueta **Resultado inicial aproximado** para comunicar que todavia existe poca evidencia.

Como regla provisional, un resultado de 80% o mas en un eje o habilidad iniciara una ruta de repaso. Un resultado inferior iniciara una ruta de nivelacion. La practica guiada agregara evidencia y recalibrara estos porcentajes con el tiempo.

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
- [ ] Definir cuando reaparece el aviso del ensayo completo despues de descartarlo.
