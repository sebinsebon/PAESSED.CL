# Security Policy

PAESSED todavia esta en fase temprana. Aun asi, el proyecto debe tratar la seguridad
y privacidad como parte de su base.

## Reportar Vulnerabilidades

Si encuentras una vulnerabilidad o riesgo de privacidad:

1. No publiques datos sensibles en un issue publico.
2. Contacta a las personas mantenedoras por el canal privado disponible en GitHub.
3. Incluye pasos para reproducir el problema y el impacto esperado.

## Datos Sensibles

Nunca subas al repositorio:

- Credenciales, tokens o llaves API.
- Datos personales de estudiantes.
- Historiales reales de respuestas.
- PDFs privados.
- Logs con informacion identificable.

## Alcance

En esta etapa, los riesgos principales son:

- Subir contenido protegido o privado.
- Mezclar datos reales con ejemplos.
- Implementar reglas de autenticacion o permisos sin pruebas.
- Dar metricas educativas con falsa precision.

Cuando el proyecto tenga codigo de aplicacion, se deberan agregar revisiones
automaticas y pruebas de permisos.
