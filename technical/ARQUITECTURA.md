# Arquitectura

## Proposito

Mantener una vision tecnica conceptual del sistema sin cerrar tecnologias o implementaciones antes de tiempo.

## Componentes conceptuales

La plataforma se puede pensar como:

Web
+
datos
+
sistema de dominio
+
banco DEMRE
+
PAES Scanner.

## Web

Contiene las areas principales: [[../product/INICIO]], [[../product/APRENDER]], [[../product/PLAYGROUND]] y [[../product/VERIFICADOR_PAES]].

## Datos

El producto necesitara modelos para usuario, preguntas, historial, dominio, estadisticas y ensayos importados. El detalle vive en [[../ROADMAP]] y documentos de sistema.

## Sistema de dominio

El sistema de dominio se define conceptualmente en [[../system/SISTEMA_ADAPTATIVO]]. Todavia no existe una formula definitiva.

## Banco DEMRE

El banco de preguntas se documenta en [[../system/BANCO_PREGUNTAS]]. Debe contener preguntas clasificadas y assets cuando corresponda.

## PAES Scanner

[[PAES_SCANNER]] es una herramienta separada de la web. Su salida esperada se conecta con [[JSON_SCHEMA]] y luego con [[../product/VERIFICADOR_PAES]].

## Por definir

- Arquitectura final de datos.
- Tecnologias concretas no esenciales.
- Separacion exacta entre cliente, servidor y procesamiento local.
- Validaciones del contrato `exam.json`.
