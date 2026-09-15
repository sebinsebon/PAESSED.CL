# Open Source Guardrails

Estas reglas ayudan a mantener PAESSED ordenado, seguro y facil de revisar.

## Decisiones

- Las ideas exploratorias van en `INBOX.md` o en documentos especificos.
- Las decisiones aceptadas van en `DECISIONS.md`.
- No trates una propuesta tecnica como decision si no aparece en `DECISIONS.md`.
- Cambios de vision principal deben actualizar `PROJECT_CONTEXT.md`.

## Alcance

Antes de implementar una funcion, debe estar claro:

- Que problema resuelve.
- Para que estudiante se esta construyendo.
- Que queda fuera del MVP.
- Como se sabra si funciona.

## Codigo

Cuando exista codigo de aplicacion:

- Mantener cambios pequenos y revisables.
- Agregar pruebas para reglas de dominio, permisos y datos.
- Preferir logica simple y explicable.
- Separar datos reales, fixtures sinteticos y configuracion local.
- No depender de secretos en archivos versionados.

## Producto Educativo

Las recomendaciones al estudiante deben ser accionables.

Evitar:

- Puntajes estimados sin metodologia clara.
- Mensajes que parezcan promesas exactas.
- Metricas que castiguen o desmotiven sin orientar.
- Gamificacion que distraiga del aprendizaje.

## IA

Si se usa IA:

- Documentar para que se usa.
- Separarla de validaciones deterministas.
- Validar resultados estructurados.
- Permitir reprocesar errores concretos.
- Evitar que contenido privado dependa de una API central si existe una alternativa local-first.
