# PAES Scanner

ESTADO: arquitectura propuesta / todavia no implementada.

## Proposito

PAES Scanner es una herramienta complementaria y separada de la web. Su objetivo seria procesar PDFs de ensayos y producir un archivo `exam.json` importable por [[../product/VERIFICADOR_PAES]].

## Enfoque

El enfoque debe ser local-first para ensayos externos o privados. El servidor de la plataforma no deberia almacenar los PDFs privados originales.

## Pipeline conceptual

PDF
-> extraccion fisica
-> representacion de paginas + texto + coordenadas
-> segmentacion semantica mediante IA con vision
-> preguntas individuales estructuradas
-> validacion
-> workers independientes para resolver pequenos grupos de preguntas
-> respuesta correcta + explicacion
-> validacion automatica
-> reprocesamiento de errores concretos
-> merge final
-> exam.json

## Ideas tecnicas consideradas

- PyMuPDF para extraccion fisica.
- Renderizar paginas a imagenes.
- No confiar unicamente en OCR.
- OCR solamente como fallback.
- Conservar coordenadas y bounding boxes.
- Poder manejar PDFs en dos columnas.
- Poder manejar preguntas cortadas entre paginas.
- Mantener el orden visual texto -> imagen -> texto.
- Alternativas que pueden contener texto o imagenes.
- Resolver preguntas en contextos independientes.
- Aproximadamente maximo 10 preguntas por worker como configuracion inicial.
- Validadores deterministas para detectar preguntas faltantes, duplicadas o JSON invalido.
- Reprocesar unicamente preguntas problematicas.
- Las imagenes podrian almacenarse como PNG durante el procesamiento y convertirse a Base64 dentro del `exam.json` final.

## Relacion con otros documentos

- [[JSON_SCHEMA]] define el contrato conceptual de salida.
- [[../product/VERIFICADOR_PAES]] define como la web podria mostrar el resultado.
- [[../DECISIONS]] registra la decision local-first para contenido privado.

## Por definir

- Formato final del pipeline.
- Herramienta CLI exacta.
- Agentes compatibles.
- Validadores definitivos.
- Estrategia de reprocesamiento.
- Manejo final de imagenes.
