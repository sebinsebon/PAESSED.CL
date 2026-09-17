# Revision de fidelidad estructural generica

Fecha: 2026-09-16. Solo desarrollo y regresion existente; sin holdout-v2 ni ensayo completo.

## Resultados de la ruta generica

| Conjunto | Complete | Partial | Assets | Crops evidence |
| --- | ---: | ---: | ---: | ---: |
| run-generic-fidelity-v1 | 3 | 5 | 16 | 8 |
| run-holdout-regression-v4 | 6 | 2 | 5 | 8 |

Desarrollo complete: 2026 P2, 2027 P5/P16. Partial: 2026 P1/P3/P4, 2027 P9/P38.
Regresion complete: 2026 P10/P20/P55, 2027 P12/P25/P60. Partial: 2026 P35, 2027 P45.

| Caso revisado | Resultado |
| --- | --- |
| 2026 P20 | text -> math -> text, formula inline preservada; complete |
| 2026 P3 | 5/6 y numero mixto 1 1/6 en orden; expresion final en un candidato atomico pendiente; partial |
| 2026 P4 | Formulas inline reordenadas; dos grupos mixtos texto/matematica sin relacion demostrada quedan pendientes; partial |
| 2027 P9 | Ecuaciones monetarias dejan de contar como texto completo: candidatos pendientes; tabla y fraccion de celda conservadas; partial |
| 2027 P45 | Fracciones, exponente y glifos de agrupacion sin transcripcion reunidos como candidato pendiente; no se afirma reconstruccion exacta; partial |

P1 tambien deja de ser complete: la expresion aritmetica y alternativas negativas estaban representadas como texto. No se introducen excepciones por numero de pregunta.

## Cobertura y limites

No se observan consumidores duplicados. Los objetos sin consumidor se clasifican layout (264 desarrollo, 198 regresion); no son prueba de que el clasificador sea infalible. Los objetos relevantes tienen representacion o unresolved: 74 objetos consumidos por unresolved en desarrollo y 40 en regresion. Incluyen los 2 objetos previamente sin reconstruccion de P38 y los 3 de P35.

La fidelidad depende de senales y relaciones geometricas implementadas. No es una garantia universal sobre expresiones nuevas. Los grupos dudosos pueden incluir texto introductorio del mismo objeto PDF; se conserva en candidate_blocks y evidence, no se descarta. AI-on-demand queda pendiente, sin llamadas automaticas.

## Verificacion

44 tests pasan. Trece tests de integracion ejecutan el CLI actual y leen drafts nuevos: nueve de fidelidad y cuatro de regresion. Los otros tests, incluidos oracle historicos, no se presentan como evidencia de fidelidad de la ruta generica. Las regresiones aceptan reconstruccion exacta o candidato atomico unresolved/partial donde no hay demostracion. Se incluyen mutaciones de draft para rechazar reordenamiento, degradacion math a text y promocion de P45 basada solo en coverage.

run-holdout-v1 y holdout-cases.json permanecen intactos. SHA256 originales verificados:

- draft.json: 00d2ebf4b767151fa105faa0b3313fbc5756e92e8e499a9b57ea38fa1e03b50e
- holdout-cases.json: b0258312c315a902cb259d607d83479a399f6ec15394ee917af3f48449605656

Los resultados previos run-generic-v1 y run-holdout-regression-v3 no se sobrescriben. Ver [[technical/ARQUITECTURA]], [[technical/JSON_SCHEMA]] y [[DECISIONS]].

## Incremento posterior: aritmetica simple y AI-on-demand

El 2026-09-17 se anadio solamente aritmetica numerica inline y ecuaciones simples. Desarrollo queda con 5 complete y 3 partial; regresion con 6 complete y 2 partial. P1 pasa a math sin resolver; P9 pasa a tres ecuaciones math inline sin resolverlas. Los casos complejos siguen bloqueados conservadoramente.

Los unresolved ahora tienen crops minimos `reason=ai_on_demand`. El flujo de host CLI usa `ai_on_demand.py` y el schema estricto; no existen adaptadores de agentes. La aplicacion registra la intervencion y fuerza revalidacion, manteniendo partial si la estructura no puede demostrarse.
