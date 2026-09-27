# Contributing

Gracias por querer contribuir a PAESSED.

Este proyecto esta en una etapa temprana, asi que valoramos especialmente cambios
que aclaren el producto, reduzcan ambiguedad y dejen mejores bases para construir.

## Antes de Contribuir

1. Lee [README.md](README.md) y el [índice de notas](notas/!HOME.md) para entender la vision.
2. Revisa [notas/ROADMAP.md](notas/ROADMAP.md) para ver prioridades actuales.
3. Revisa [docs/DECISIONS.md](docs/DECISIONS.md) para no reabrir decisiones aceptadas sin motivo claro.
4. Lee `docs/DATA_AND_CONTENT_POLICY.md` antes de agregar contenido, ejemplos o datasets.

## Tipos de Contribuciones

Son bienvenidas:

- Mejoras a documentacion, arquitectura y decisiones.
- Propuestas de taxonomia PAES M1 con fuentes verificables.
- Especificaciones de flujos de producto.
- Reglas adaptativas simples, explicables y testeables.
- Prototipos o codigo con pruebas basicas.
- Correcciones de errores, ambiguedades o inconsistencias.

Evita contribuir:

- PDFs privados o material protegido sin permiso.
- Datos reales de estudiantes.
- Logica opaca dificil de explicar o probar.
- Cambios grandes sin abrir primero una discusion o issue.

## Flujo Sugerido

1. Abre un issue describiendo el problema o propuesta.
2. Espera feedback si el cambio afecta producto, datos, arquitectura o contenido.
3. Crea una rama con nombre claro.
4. Haz cambios pequenos y revisables.
5. Abre un pull request con contexto, decisiones y pruebas realizadas.

## Criterios Para Pull Requests

Un PR deberia explicar:

- Que cambia.
- Por que cambia.
- Que documentos o decisiones toca.
- Que riesgos tiene.
- Como se probo o reviso.

Si el cambio agrega codigo, incluye pruebas o una explicacion de por que no aplican todavia.

## Estilo de Documentacion

- Usa Markdown simple.
- Prefiere frases claras sobre jerga.
- Mantiene las decisiones aceptadas en [docs/DECISIONS.md](docs/DECISIONS.md).
- Mantiene ideas exploratorias fuera de [docs/DECISIONS.md](docs/DECISIONS.md) hasta que se acepten.
- Usa nombres de archivos y carpetas existentes cuando sea posible.


## Organización

`docs/` contiene documentación técnica vigente y decisiones. `notas/` es el vault
de Obsidian para planificación y producto. Usa enlaces Markdown relativos en
la documentación técnica y wikilinks solo entre notas del vault. Los scripts,
schemas y la skill permanecen en `skills/`; no moverlos al vault. Los resultados
privados viven fuera del repositorio. Evita repetir estados o contratos: enlaza
a la referencia vigente. Conserva los informes fechados como historial.
