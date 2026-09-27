---
title: PAESSED — notas de trabajo
aliases:
  - PROJECT_CONTEXT
  - IDEA_GENERAL
tags:
  - paessed
  - planificacion
---

# PAESSED — notas de trabajo

Este es el inicio del vault **`PAESSED.CL/notas`**. Aquí viven las ideas,
planificación, diseño y especificaciones de producto. El código y sus contratos
viven fuera del vault, en el mismo repositorio.

## Qué estamos construyendo

Una plataforma para preparar PAES M1 que detecte fortalezas y debilidades y
adapte el aprendizaje: diagnóstico -> perfil -> ruta -> práctica -> nuevos
resultados -> adaptación. El foco es M1; otras pruebas se evaluarán después.
PAESSED es el nombre de trabajo actual; el nombre comercial definitivo no se
considera cerrado en estas notas.

El MVP acordado es gratuito, sin publicidad y open source. Incluye diagnóstico
de 12 preguntas, Inicio, nivelación y Aprender, estadísticas, ensayo completo
opcional y revisión de ensayos importados. Playground y Ranking aparecen como
expansiones, no bloquean ese recorrido. El piloto previsto comienza con cinco
estudiantes de confianza. Esto describe el producto acordado, no una web ya
implementada.

## Ahora

```text
PDF -> reconstruir (draft) -> revisar fidelidad (verified)
    -> comprobar respuestas y explicaciones (final) -> mostrar en la web
```

Estamos preparando la revisión independiente del contenido extraído por el
importador. La referencia vigente es [Pipeline y estado](../docs/IMPORTADOR.md).
No dupliques aquí los conteos de pruebas ni los benchmarks: cambian con cada
checkpoint y se registran allí con su alcance.

- [[ROADMAP]]: tareas y fases del producto. Sus fases no son las tres etapas del importador.
- [[INBOX]]: ideas todavía no convertidas en decisiones.
- [Decisiones aceptadas](../docs/DECISIONS.md): registro canónico, fuera del vault.
- [Contrato draft v1](../docs/DRAFT_V1_CONTRACT.md): referencia técnica.
- [Repositorio](../README.md): código, herramientas y colaboración.

## Producto

- [[producto/INICIO]]: diagnóstico, dashboard y siguiente actividad.
- [[producto/APRENDER]]: ruta guiada y práctica adaptativa.
- [[producto/PLAYGROUND]]: práctica libre futura.
- [[producto/VERIFICADOR_PAES]]: producto web para ensayos y respuestas del estudiante; distinto de la revisión técnica de Etapa 2.
- [[sistema/ESTRUCTURA_M1]]: taxonomía inicial y fuentes curriculares.
- [[sistema/SISTEMA_ADAPTATIVO]]: dominio y recomendaciones pendientes de concretar.
- [[sistema/ESTADISTICAS]]: métricas y límites de interpretación.
- [[sistema/BANCO_PREGUNTAS]]: requisitos del banco, revisión y publicación.
- [[DISENO]]: criterios, referencias y anotaciones visuales.

## Principios

Personalización, aprendizaje centrado en debilidades, sesiones manejables y
gamificación que ayude. Separar reglas deterministas de tareas de IA, extracción
de revisión y resolución, e importación privada de publicación. Usar contenido
oficial o autorizado cuando corresponda y comprobar sus permisos. No depender
de una API central obligatoria para el importador; el CLI del usuario presta la
capacidad de IA. Definir el producto antes de sobredimensionar su arquitectura.

## Dudas de producto aún abiertas

- Cómo calcular dominio, cuándo saltar contenido, subir dificultad o repasar prerrequisitos.
- Cuánto influyen aciertos, errores, omisiones y preguntas repetidas.
- Qué peso tendrán Playground y otras actividades en el perfil.
- Cómo comunicar incertidumbre y si habrá una estimación de puntaje responsable.
- Qué tono visual conviene y qué métricas ayudan sin abrumar.
- Qué contenido concreto formará el diagnóstico y el banco piloto.

El alcance del MVP y la taxonomía inicial ya están definidos; su implementación,
selección de contenido y validación con estudiantes siguen pendientes.

## Cómo mantenerlo ordenado

Idea -> [[INBOX]]. Tarea -> [[ROADMAP]]. Diseño -> nota de producto pertinente.
Decisión aceptada -> [DECISIONS](../docs/DECISIONS.md). Comportamiento técnico
vigente -> [IMPORTADOR](../docs/IMPORTADOR.md) o su contrato. Informes fechados
-> [historial técnico](../docs/historial/IMPORTADOR_2026-09.md); evidencia privada
-> `Ensayos/ejecuciones/`, fuera de Git.

No guardar PDFs, credenciales ni datos de estudiantes aquí. Los adjuntos de
Obsidian están en `adjuntos/` y las vistas locales en `bases/`, ignorados por Git.
Las imágenes o referencias locales no adquieren permiso de publicación por
formar parte del vault. Los enlaces Markdown a `../docs/` salen del vault:
consúltalos con el editor o en GitHub si Obsidian no permite abrirlos.
