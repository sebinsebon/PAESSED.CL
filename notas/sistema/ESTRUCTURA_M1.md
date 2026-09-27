# Estructura M1

## Proposito

Definir la taxonomia curricular de PAES Matematica M1 que usara la plataforma sin confundir contenidos con habilidades transversales.

## Fuente oficial vigente

La referencia principal del proyecto es el **Temario PAES Regular de Competencia Matematica 1 (M1), Proceso de Admision 2027**, publicado por DEMRE el 19 de marzo de 2026:

- Pagina oficial: https://demre.cl/publicaciones/2027/2027-26-03-19-temario-paes-regular-m1
- PDF oficial: https://demre.cl/publicaciones/pdf/2027-26-03-19-temario-paes-regular-m1.pdf
- Referencia curricular: formacion general desde 7 basico hasta 2 medio.
- Formato oficial: 65 preguntas de seleccion multiple, 60 consideradas para el puntaje, 4 opciones y 2 horas 20 minutos.

El temario de Invierno 2027 es mas acotado: no incluye la unidad de semejanza y proporcionalidad de figuras y no menciona cilindros en cuerpos geometricos. PAESSED no debe mezclar ambos temarios ni usar el de Invierno como catalogo principal del ensayo regular.

## Habilidades oficiales

Las habilidades son una dimension transversal. No son temas ni ramas subordinadas de una unidad.

| ID interno propuesto | Habilidad DEMRE |
|---|---|
| `resolver_problemas` | Resolver problemas |
| `modelar` | Modelar |
| `representar` | Representar |
| `argumentar` | Argumentar |

## Ejes y unidades oficiales

La PAES Regular M1 2027 contiene 4 ejes y 16 unidades tematicas.

| Eje | ID interno propuesto | Unidad tematica | Alcance oficial resumido |
|---|---|---|---|
| Numeros | `num_enteros_racionales` | Conjunto de los numeros enteros y racionales | Operaciones, orden, comparacion y problemas contextualizados. |
| Numeros | `num_porcentaje` | Porcentaje | Concepto, calculo y problemas contextualizados. |
| Numeros | `num_potencias_raices` | Potencias y raices enesimas | Propiedades, descomposicion y problemas en los numeros reales. |
| Algebra y funciones | `alg_expresiones` | Expresiones algebraicas | Productos notables, factorizacion, operatoria y problemas. |
| Algebra y funciones | `alg_proporcionalidad` | Proporcionalidad | Proporcion directa e inversa, representaciones y problemas. |
| Algebra y funciones | `alg_ecuaciones_inecuaciones` | Ecuaciones e inecuaciones de primer grado | Resolucion y problemas lineales. |
| Algebra y funciones | `alg_sistemas_2x2` | Sistemas de ecuaciones lineales (2x2) | Resolucion y problemas contextualizados. |
| Algebra y funciones | `alg_funcion_lineal_afin` | Funcion lineal y afin | Conceptos, tablas, graficos y problemas. |
| Algebra y funciones | `alg_funcion_cuadratica` | Funcion cuadratica | Ecuaciones de segundo grado, parametros, grafica, vertice, ceros e intersecciones. |
| Geometria | `geo_figuras` | Figuras geometricas | Pitagoras, perimetros y areas de triangulos, paralelogramos, trapecios y circulos. |
| Geometria | `geo_cuerpos` | Cuerpos geometricos | Superficie y volumen de paralelepipedos, cubos y cilindros. |
| Geometria | `geo_transformaciones` | Transformaciones isometricas | Puntos, vectores, rotacion, traslacion y reflexion. |
| Geometria | `geo_semejanza` | Semejanza y proporcionalidad de figuras | Propiedades de semejanza, modelos a escala y proporcionalidad. |
| Probabilidad y estadistica | `pro_datos_graficos` | Representacion de datos mediante tablas y graficos | Frecuencias, tipos de graficos, promedio y problemas. |
| Probabilidad y estadistica | `pro_medidas_posicion` | Medidas de posicion | Cuartiles, percentiles, diagramas de cajon y problemas. |
| Probabilidad y estadistica | `pro_reglas_probabilidad` | Reglas de las probabilidades | Probabilidad de un evento y reglas aditiva y multiplicativa. |

Los IDs internos deben ser estables e inmutables. Los nombres visibles y la version del temario pueden cambiar sin romper respuestas historicas.

## Modelo minimo para el MVP

- Jerarquia navegable: **Eje -> Unidad tematica**.
- Cada pregunta debe tener una unidad y una habilidad primaria obligatoria. Puede tener una habilidad secundaria opcional.
- La habilidad funciona como etiqueta transversal; no se construye una matriz visible de 16 unidades por 4 habilidades.
- Las recomendaciones de estudio apuntan a una unidad concreta. La habilidad explica el tipo de razonamiento que debe practicar el estudiante.
- Las respuestas se guardan en forma granular para poder recalcular estadisticas cuando cambien las reglas.
- El catalogo se versiona como `DEMRE_REGULAR_2027`. Una version futura crea un catalogo nuevo sin alterar respuestas historicas.

## Prerrequisitos iniciales

Los prerrequisitos son recomendaciones blandas. Ninguna unidad queda bloqueada y no existe un test de desbloqueo. El estudiante puede entrar a cualquier contenido.

| Prerrequisito recomendado | Unidad que apoya | Razon inicial |
|---|---|---|
| `num_enteros_racionales` | `num_porcentaje` | El porcentaje usa razones, fracciones y operatoria. |
| `num_enteros_racionales` | `num_potencias_raices` | La unidad opera con bases y exponentes racionales. |
| `num_enteros_racionales` | `alg_expresiones` | La operatoria algebraica requiere manejo numerico basico. |
| `alg_expresiones` | `alg_ecuaciones_inecuaciones` | Resolver requiere transformar expresiones. |
| `alg_ecuaciones_inecuaciones` | `alg_sistemas_2x2` | Los sistemas combinan ecuaciones lineales. |
| `alg_proporcionalidad` | `alg_funcion_lineal_afin` | La proporcionalidad directa apoya la funcion lineal. |
| `alg_ecuaciones_inecuaciones` | `alg_funcion_lineal_afin` | Apoya el trabajo con relaciones lineales. |
| `alg_expresiones` | `alg_funcion_cuadratica` | La operatoria y factorizacion aparecen en cuadraticas. |
| `alg_ecuaciones_inecuaciones` | `alg_funcion_cuadratica` | La unidad incluye ecuaciones de segundo grado. |
| `num_potencias_raices` | `alg_funcion_cuadratica` | Las raices aparecen al resolver ciertas cuadraticas. |
| `geo_figuras` | `geo_cuerpos` | Areas planas apoyan superficies y volumenes. |
| `geo_figuras` | `geo_semejanza` | La semejanza opera sobre propiedades de figuras. |
| `alg_proporcionalidad` | `geo_semejanza` | Modelos a escala requieren proporcionalidad. |
| `pro_datos_graficos` | `pro_medidas_posicion` | Cuartiles y diagramas requieren interpretar datos ordenados. |

`geo_transformaciones` y `pro_reglas_probabilidad` quedan sin prerrequisito obligatorio inicial. La relacion entre racionales y probabilidad puede usarse como recomendacion contextual mas adelante, si las preguntas reales muestran que aporta valor.

Estas relaciones son una hipotesis pedagogica inicial. Deben contrastarse con preguntas oficiales permitidas y con el piloto antes de afectar con fuerza la seleccion de actividades.

## Reglas del motor para el MVP

- Todos los ejes y unidades estan disponibles desde el inicio.
- Un error repetido puede activar la sugerencia de un prerrequisito inmediato.
- Se permiten recomendaciones entre ejes, por ejemplo Proporcionalidad -> Semejanza.
- El motor no recorre cadenas completas ni bloquea contenido.
- La interfaz debe explicar por que recomienda el repaso.

## Evidencia y estadisticas

El test corto no puede medir con precision las 16 unidades y las 4 habilidades a la vez.

- Inicio mostrara los 4 ejes y las 4 habilidades como dimensiones separadas; no mostrara 64 combinaciones.
- Despues del test corto se mostraran porcentajes con la etiqueta **Resultado inicial aproximado**.
- No se mostrara un contador de evidencia ni se bloquearan porcentajes en el MVP.
- El ensayo completo y la practica guiada agregaran evidencia y reemplazaran gradualmente las estimaciones iniciales.

## Limites

- Que un contenido aparezca en el temario no garantiza que aparezca en cada prueba.
- Todo el contenido preguntado debe desprenderse del temario oficial.
- Dificultad, microtemas, orden pedagogico y prerrequisitos son decisiones internas; no deben presentarse como clasificaciones oficiales de DEMRE.
- El porcentaje de aciertos del producto no equivale directamente a puntaje PAES. La transformacion oficial depende de la forma rendida y su equiparacion.

## Pendientes

- [x] Investigar estructura oficial y actualizada de PAES M1.
- [x] Definir y validar la taxonomia interna inicial.
- [x] Definir prerrequisitos inmediatos entre unidades.
- [ ] Validar la taxonomia contra preguntas oficiales y material autorizado.
- [ ] Separar contenido esencial de contenido avanzado para la ruta de [[producto/APRENDER]].
- [ ] Versionar el catalogo cuando DEMRE publique un nuevo temario.

Esta estructura debe mantenerse compatible con [[sistema/SISTEMA_ADAPTATIVO]] y [[sistema/BANCO_PREGUNTAS]].
