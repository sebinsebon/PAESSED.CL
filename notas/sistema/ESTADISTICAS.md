# Estadisticas

## Proposito

Organizar las metricas que podrian mostrarse al estudiante y las que podrian usar internamente los sistemas de aprendizaje.

## Metricas posibles

- Porcentaje por eje.
- Porcentaje por tema.
- Evolucion del rendimiento.
- Racha.
- Preguntas realizadas.
- Precision.
- Dominio por habilidad.
- Puntaje estimado.
- Preguntas falladas.
- Preguntas omitidas.
- Tiempo de practica, si se decide registrarlo.

## Uso en producto

Las estadisticas podrian aparecer en [[producto/INICIO]], [[producto/PLAYGROUND]] y [[producto/VERIFICADOR_PAES]].

No todas las metricas deben mostrarse al usuario. Algunas pueden ser internas para [[sistema/SISTEMA_ADAPTATIVO]].

Los porcentajes se calcularan por eje y habilidad. Deben evolucionar a medida que el estudiante complete practica guiada, el ensayo PAES completo o ensayos externos confirmados. La interfaz debe indicar cuando la evidencia sea escasa y evitar presentar el porcentaje como una medicion exacta.

## Puntaje estimado

El puntaje estimado requiere cuidado. Debe evitar falsa precision y probablemente necesita una metodologia clara antes de aparecer en el producto.

## Por definir

- Que metricas van al MVP.
- Como calcular dominio.
- Como estimar puntaje PAES.
- Como mostrar incertidumbre.
- Cuanto peso tienen preguntas repetidas.
- Como diferenciar diagnostico, Aprender, Playground y ensayos importados.

## Pendientes

- [ ] Definir metricas visibles.
- [ ] Definir metricas internas.
- [ ] Definir historico de dominio.
- [ ] Definir tratamiento de preguntas repetidas.
