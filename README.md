# PAESSED

PAESSED es una plataforma abierta de preparación para PAES Matemática M1:
diagnóstico, perfil de dominio, práctica guiada y adaptación del aprendizaje.
El MVP acordado será gratuito y sin publicidad. La aplicación web está pendiente;
la parte ejecutable actual es el importador local de contenido.

## Dónde está cada cosa

| Carpeta o archivo | Función |
| --- | --- |
| [docs/IMPORTADOR.md](docs/IMPORTADOR.md) | Guía vigente del pipeline, estado, límites y siguiente paso |
| [docs/DRAFT_V1_CONTRACT.md](docs/DRAFT_V1_CONTRACT.md) | Contrato técnico de `draft.json` v1 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decisiones aceptadas y su historial |
| [skills/paes-importer/](skills/paes-importer/) | Skill, scripts y esquemas ejecutables de Etapa 1 |
| [tests/](tests/) y [tools/](tools/) | Regresiones y herramientas locales |
| [notas/!HOME.md](notas/!HOME.md) | Vault de Obsidian: planificación, producto, ideas y diseño |
| [notas/ROADMAP.md](notas/ROADMAP.md) | Prioridades del proyecto y pendientes del MVP |
| [docs/historial/](docs/historial/) | Informes históricos; no describen el estado actual |

Abre **`PAESSED.CL/notas` como vault de Obsidian**, en lugar de la raíz del
repositorio. Las notas siguen en el mismo Git; no son privadas por estar en
esa carpeta. La configuración de Obsidian, adjuntos locales y vistas `.base`
se mantienen fuera de Git. `Ensayos/`, con PDFs, ejecuciones y prototipos
privados, permanece como carpeta hermana del repositorio.

## Pipeline de contenido

```text
PDF obligatorio + solucionario opcional
  -> Etapa 1: reconstrucción -> draft.json + assets/ + evidence/
  -> Etapa 2: revisión independiente de fidelidad -> verified.json
  -> Etapa 3: respuestas y mini explicaciones comprobadas -> final.json
  -> PAESSED Web: importar y renderizar
```

Etapa 1 y el productor v1 están implementados con límites conocidos. Etapas 2
y 3, el contrato final y el importador web siguen pendientes. `verified` dentro
de un borrador no equivale a una revisión visual independiente. Consulta el
[estado y las validaciones registradas](docs/IMPORTADOR.md#estado-actual) antes
de ampliar una ejecución; las muestras no acreditan un ensayo completo.

Importar un ensayo personal no lo publica en el banco. El banco público
requerirá aprobaciones de fidelidad, contenido educativo y derechos sobre una
versión exacta. Esa barrera todavía no está implementada.

## Producto y colaboración

Inicio y Aprender forman el recorrido guiado; el Verificador web permitirá
revisar ensayos importados y resultados del estudiante. Playground y Ranking
son expansiones posteriores. Las especificaciones están en el
[índice de notas](notas/!HOME.md).

Lee [CONTRIBUTING.md](CONTRIBUTING.md), las
[reglas del proyecto](docs/OPEN_SOURCE_GUARDRAILS.md) y la
[política de contenido](docs/DATA_AND_CONTENT_POLICY.md) antes de contribuir.
No se deben publicar PDFs privados, preguntas o imágenes sin permiso, datos
de estudiantes ni credenciales. La licencia [MIT](LICENSE) del código y la
documentación propia no concede derechos sobre material de terceros.
