# JSON Schema

## Proposito

Definir el contrato entre PAES Scanner y el visualizador web del [[../product/VERIFICADOR_PAES]].

## Estado

Este documento describe un ejemplo conceptual. Todavia no es necesariamente el schema definitivo.

## Ejemplo conceptual

```json
{
  "numero": 14,
  "eje": "geometria",
  "tema": null,
  "bloques": [
    {
      "tipo": "texto",
      "contenido": "..."
    },
    {
      "tipo": "imagen",
      "src": "data:image/png;base64,..."
    }
  ],
  "opciones": [
    {
      "letra": "A",
      "tipo": "texto",
      "contenido": "..."
    }
  ],
  "respuesta_correcta": "B",
  "explicacion": "..."
}
```

## Campos esperados

- `numero`: numero de pregunta.
- `eje`: eje curricular, si se conoce.
- `tema`: tema, si se conoce.
- `bloques`: contenido de la pregunta en orden visual.
- `opciones`: alternativas.
- `respuesta_correcta`: letra correcta.
- `explicacion`: explicacion generada o validada.

## Por definir

- Schema completo de `exam.json`.
- Campos obligatorios y opcionales.
- Representacion de imagenes.
- Validaciones deterministas.
- Como representar respuestas del estudiante.
- Como representar preguntas omitidas.
- Versionado del schema.
