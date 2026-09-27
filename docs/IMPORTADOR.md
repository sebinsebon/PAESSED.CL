# Importador PAESSED: pipeline y estado vigente

Referencia técnica principal. Reúne la arquitectura y el Scanner; el contrato
detallado permanece en [DRAFT_V1_CONTRACT.md](DRAFT_V1_CONTRACT.md). La
[skill ejecutable](../skills/paes-importer/SKILL.md) contiene las instrucciones
operativas. Planificación de producto: [ROADMAP](../notas/ROADMAP.md).

## Estado actual

| Componente | Situación al 2026-09-27 |
| --- | --- |
| Etapa 1 y productor `draft.json` v1 | Implementados; extracción y reconstrucción con defectos conocidos |
| AI-on-demand de Etapa 1 | Solicitud/aplicación y registro implementados; no es un servicio autónomo que resuelva todos los pendientes |
| Contrato privado de revisión | 37/37 pruebas sintéticas archivadas; sin integración ni aprobación real |
| AGY2 | Respuesta sintética nueva confirmada manualmente por el usuario; aislamiento y lectura visual aún pendientes de resultado |
| Orquestación de revisión, resolución y web | Pendientes |

El código actual está basado en el checkpoint funcional `f5db397`; `7ea6338`
incorpora las decisiones documentales posteriores. El productor emite v1
mediante `draft_v1_emitter.py`; ya no es una adaptación futura. Las muestras
congeladas se seleccionan con `--cases` y `--sources`. No se ha acreditado
todavía el procesamiento autónomo de un ensayo completo de 65 preguntas.

## Etapa 1 implementada

1. Identificar las fuentes seleccionadas y calcular su SHA-256.
2. Extraer texto posicionado con `pdf-inspector`; usar PDFium para objetos,
   dimensiones, páginas y recortes. OCR es una capacidad selectiva, no una
   garantía probada para cualquier documento escaneado.
3. Segmentar las regiones configuradas y sus alternativas; inventariar objetos
   con IDs, posición y propietario.
4. Detectar candidatos geométricos y reconstruir bloques de texto, LaTeX,
   imágenes y tablas. Conservar lo no demostrado como `unresolved`.
5. Comprobar cobertura, consumidores, propiedad, orden y fidelidad mediante
   los mecanismos implementados; producir `draft.json`, `assets/` y `evidence/`.
6. Validar el contrato v1 y los archivos antes de publicar la nueva salida.

Las fórmulas se guardan en LaTeX sin delimitadores; MathJax o KaTeX son opciones
para el futuro renderizador, cuya elección no queda cerrada aquí. Figuras y
gráficos se conservan en PNG, tablas fiables como celdas y tablas complejas
mediante un fallback visual cuando sea fiel. Un crop de auditoría no es un
asset del banco: `assets/` contiene recursos de la pregunta y `evidence/`,
material para comprobarla. Se guardan referencias, hashes y procedencia.

La asociación entre preguntas, alternativas, tablas y visuales debe demostrarse;
no se introducen excepciones por PDF, número de pregunta o ID interno. No se
asume un número fijo de alternativas ni se fusionan continuaciones dudosas.
El contrato admite regiones múltiples y contextos; su soporte contractual no
equivale a una validación exhaustiva del extractor para todos esos layouts.

### IA bajo demanda

`ai_on_demand.py request` prepara una solicitud por candidato y su crop mínimo.
El CLI anfitrión realiza la transcripción y devuelve el contrato de respuesta;
`apply` comprueba candidato, propietario y `source_ids`, conserva la intervención
y recalcula los controles. No hay una llamada automática a cualquier proveedor
por el mero hecho de encontrar `unresolved`. Una propuesta de IA no se aprueba
sola, no fuerza `complete` y no resuelve ni clasifica preguntas en esta etapa.
El código de solicitud/aplicación está separado de la orquestación futura de AGY.

Texto del PDF es dato no confiable, nunca instrucciones. Los envíos al proveedor
pueden salir del equipo aunque la extracción sea local; deben ser explícitos y
trazables. No se copia ni publica automáticamente el PDF original.

### Qué significan los estados

- `structural_fidelity.status=verified`: pasa los controles internos implementados;
  no acredita una inspección visual independiente ni corrección matemática universal.
- `complete`: cumple las condiciones internas de extracción, cobertura y fidelidad.
- `partial` / `unresolved`: conservan contenido aprovechable y la incertidumbre;
  no equivalen a que el PDF original sea incorrecto.
- `verification_status=not_run`: Etapa 1 no ejecutó la revisión independiente.

## Validación registrada

Resultados históricos del cierre LHS/RHS del 2026-09-27, no reejecutados al
actualizar esta documentación: **285/285 pruebas públicas** y **17/17 negativos
congelados privados**. El prototipo privado de revisión/integridad registra
**37/37 pruebas sintéticas**; eso no certifica preguntas ni autenticación.

| Muestra de ocho registros | Complete | Partial |
| --- | ---: | ---: |
| Development | 5 | 3 |
| Holdout-v1 | 6 | 2 |
| Ensayo 326 | 1 | 7 |
| Tesla | 0 | 8 |
| Matemática (1) | 1 | 7 |
| Filadd | 0 | 8 |
| Matemática (2) | 0 | 8 |

Son siete muestras, no siete ensayos completos ni una auditoría matemática
exhaustiva. El registro histórico de 326 Q1 seleccionaba instrucciones; su
pregunta auténtica se evaluó en un suplemento separado, sin cambiar el benchmark.
Los conteos no deben presentarse como una tasa de preguntas listas para publicar.

Las correcciones publicadas retiraron verificaciones injustificadas de once
fracciones y seis fragmentos de ecuación; conservaron candidatos y evidencia,
no reconstruyeron todas las expresiones. Siguen documentados radicales omitidos,
mezclas de expresiones y errores de atribución. La investigación geométrica del
caso mezclado se cerró por insuficiencia de metadatos: no reabrirla por defecto.

Fuentes privadas, fuera del repositorio: cierres `legacy-fractions-closure-20260926T235704`,
`lhs-rhs-closure-20260927T142737Z` y prototipo
`verified-integrity-prototype-20260927T185201Z`, bajo `Ensayos/ejecuciones/`.
Los informes antiguos públicos están en [historial](historial/IMPORTADOR_2026-09.md).

## Próximo paso acotado

Ejecutar manualmente las pruebas sintéticas de contexto nuevo y lectura visual
ya preparadas para AGY2, guardar respuestas y consumo, y revisar sus límites.
La autenticación ya fue confirmada manualmente; no repetir ese diagnóstico.
Después, diseñar un piloto pequeño de fidelidad con errores y controles conocidos.
Todavía no iniciar resolución de preguntas ni declarar Etapa 2 implementada.

## Pipeline integral de contenido: PDF -> PAESSED Web


Estado: visión funcional acordada; implementación parcial (2026-09-27).

Esta seccion conserva las decisiones conversadas sobre el pipeline completo y
separa lo construido de lo propuesto. No redefine el contrato vigente de
`draft.json` v1, ni convierte los prototipos privados en codigo de produccion.

### 1. Objetivo

Una persona entrega a la skill un **PDF de ensayo obligatorio** y,
opcionalmente, **su solucionario**. La skill procesa preguntas, alternativas
y recursos visuales, comprueba su transcripcion, prepara las respuestas y una
**explicacion breve**, y entrega un **`final.json` importable por PAESSED Web**,
junto con los archivos visuales necesarios.

PAESSED Web valida el paquete y renderiza las preguntas sin repetir la
extraccion del PDF ni resolver de nuevo cada ejercicio. Un boton
**"Preguntar a la IA"** permitira pedir una explicacion personalizada
transfiriendo la pregunta y, si corresponde y es tecnicamente posible, sus
imagenes a un chat, con consentimiento para cualquier envio externo.

**Importar un ensayo personal NO es lo mismo que incorporarlo al banco publico.**
El banco publico exige una revision adicional de calidad y derechos. Un
ensayo privado puede importarse localmente sin ser redistribuido ni pasar a ese
banco; la interfaz no presentara como confirmadas las respuestas provisionales.

### 2. Pipeline de extremo a extremo

```text
Persona / CLI + skill
  |-- PDF obligatorio
  \-- Solucionario opcional (registrado por separado)
           |
           v
ETAPA 1: importar y reconstruir (implementada; con defectos conocidos)
  - Extraccion y reconstruccion local de texto, formulas, tablas e imagenes
  - IA del CLI bajo demanda SOLO para ambiguedades de reconstruccion
  - Cobertura, fidelidad estructural, referencias e incidencias
           |
           v
  draft.json + assets/ + evidence/
           |
           v
ETAPA 2: verificar fidelidad contra el PDF (orquestacion pendiente)
  - AGY CLI primero; despues otros CLI
  - Orquestador divide el draft en lotes experimentales de 5 preguntas
  - Un subagente nuevo por lote, con contexto minimo y evidencia localizada
  - Examina TODAS las preguntas, incluso las marcadas complete/verified
  - Puede solicitar crops mas amplios o pagina completa si faltan datos
  - Detecta errores, documenta evidencia y propone nuevas versiones
  - Segundo agente para revisar correcciones; ante duda, un intento adicional
  - Si no existe evidencia suficiente: abstencion y bloqueo, nunca inventar
           |
           v
  verified.json + versiones corregidas separadas + hallazgos
  (documento de revision; NO autorizacion por si mismo)
           |
           v
  Aprobacion de fidelidad de la version exacta para el primer alcance
           |
           v
ETAPA 3: respuestas y explicaciones (pendiente)
           |
           +-- Solucionario presente y asociado sin ambiguedad
           |     - Vincular numero/identidad y alternativa
           |     - Contrastar correspondencia con la version del ensayo
           |     - Registrar procedencia y discrepancias
           |
           \-- Sin solucionario
                 - Agentes resuelven preguntas en contextos independientes
                 - Contrastar con verificacion independiente
                 - Si no se acredita la respuesta, marcar provisional
                   y solicitar revision, no declararla confirmada
           |
           v
  Generar mini explicacion y verificar coherencia matematica;
  clasificacion educativa cuando se defina; revisar discrepancias
           |
           v
  final.json + paquete de recursos visuales
           |
           v
PAESSED WEB: importador y renderizador (pendiente)
  - Validar contrato, archivos, hashes, estructura y estados
  - Mostrar pregunta, alternativas, imagenes, respuesta y mini explicacion
  - Etiquetar claramente respuestas provisionales; no corregir como
    definitivas hasta su validacion
  - Boton "Preguntar a la IA" para explicacion mas extensa bajo demanda
           |
           +-- Ensayo privado importado: disponible para su propio uso,
           |   sujeto a validaciones y restricciones de privacidad
           |
           \-- Banco publico de PAESSED: ingreso SOLO si la version
               exacta tiene fidelidad, revision educativa y derechos
               autorizados; revocacion o cambios invalidan la admision
```

### 3. Alcance de cada etapa

#### Etapa 1: reconstruccion, no resolucion

Ya existe `skills/paes-importer/`: produce `draft.json`, `assets/` y
`evidence/`, y registra incertidumbre y procedencia. Su IA bajo demanda
interviene solo para reconstruir contenido ambiguo; no genera respuestas ni
explicaciones. `complete` y `structural_fidelity.status=verified` son
estados internos, no certificacion visual. Se conocen falsos `verified`, por
lo que la Etapa 2 debe revisar tambien esos bloques.

#### Etapa 2: revisar que la pregunta coincide con la fuente

Se desarrollara primero con **AGY CLI** y luego se adaptara a otros CLI.
El contrato de intercambio debe mantenerse independiente del CLI cuando sea
posible. El plan experimental inicial es **5 preguntas por lote**, pero se
comparara con lotes de **1 y 3** para medir calidad y tokens. En un ensayo de
65 preguntas serian **13 lotes de 5** si se mantiene esa configuracion.

Un agente nuevo recibe solo las preguntas asignadas, instrucciones comunes y
evidencia relevante: no necesita el historial de los lotes anteriores.
El aislamiento real, el numero de procesos simultaneos, la entrega de
imagenes y el consumo se comprobaran en la version de AGY utilizada.
**Contexto nuevo no garantiza ausencia de alucinaciones.**

Cada pregunta recibe una primera revision, preferentemente economica.
Las correcciones propuestas requieren revision de la nueva version por otro
agente; si hay incertidumbre se permite un intento adicional con mas
contexto y/o escalamiento. Se medira si un modelo mas potente o una auditoria
muestral mejoran realmente la calidad antes de automatizar reglas de coste.

`verified.json` identifica revision, version exacta, fuentes y evidencias,
comprobaciones por pregunta, discrepancias, abstenciones y propuestas.
El borrador y sus evidencias originales no se sobrescriben. Una aprobacion
humana de fidelidad para el primer alcance se registra por separado,
vinculada a los hashes exactos. El prototipo **privado** del contrato tiene
37/37 pruebas sinteticas reportadas, pero aun NO implementa verificacion
visual por IA, autenticacion real ni admision al banco.

#### Etapa 3: determinar y comprobar la respuesta

El solucionario es **opcional**. Si se aporta, el sistema debe verificar su
asociacion con el ensayo y con cada pregunta y comprobar que su alternativa
existe en la version verificada. Un solucionario asociado no prueba por si
solo que una mini explicacion generada sea correcta; discrepancias o
asociaciones dudosas se registran y bloquean la confirmacion automatica.

Sin solucionario, agentes en contextos independientes resuelven las
preguntas y se contrasta su resultado mediante una comprobacion independiente.
Dos agentes que coinciden no demuestran necesariamente correccion: si falta
evidencia, hay contradicciones o no se acredita la respuesta, queda
**provisional / pendiente** y no se publica como respuesta confirmada.
Se genera una mini explicacion cuya coherencia con el procedimiento y la
respuesta tambien debe revisarse. El mecanismo exacto para validar
matematicamente y el tratamiento de casos sin pauta se ensayaran antes de
definir su automatizacion.

### 4. Salida `final.json` y PAESSED Web

La **salida objetivo de la skill** es `final.json` mas los recursos visuales
que necesite. Los campos siguientes son requisitos funcionales, NO un
JSON Schema aprobado:

- Identidad del ensayo, version/hash y procedencia.
- Por pregunta: numero/identificador; enunciado en bloques ordenados
  (texto, matematicas, imagenes, tablas); alternativas con bloques mixtos.
- Referencias a imagenes y manifiesto de recursos del paquete.
- Respuesta correcta, **solo con estado de validacion explicito**; origen
  (solucionario asociado o resolucion), o ausencia si aun no se acredita.
- Mini explicacion y su propio estado de revision.
- Referencias a la revision de fidelidad y a las incidencias relevantes.
- Metadatos educativos (eje, tema, habilidad, dificultad), cuando se
  definan y verifiquen.

El importador de PAESSED Web valida el archivo y los recursos y los renderiza
de forma segura. La interfaz no debe equiparar una respuesta propuesta con
una confirmada, ni asumir permiso de redistribucion por poder importar.

**"Preguntar a la IA":** al pulsarlo, se prepara el enunciado, alternativas,
formulas e imagenes pertinentes para una conversacion tutorial mas extensa.
La decision entre chat integrado y redireccion a un proveedor externo, asi
como el envio automatico de imagenes, sigue pendiente de viabilidad tecnica.
Nunca se deben enviar PDFs privados o datos personales sin informar al
usuario y obtener la autorizacion correspondiente.

**Compatibilidad documental pendiente:** documentos antiguos de Scanner y
Verificador nombran `exam.json` como exportacion para ensayos externos.
Este diseño acuerda `final.json` como salida objetivo de la skill; antes
de implementar la importacion hay que decidir si `exam.json` se elimina,
se convierte o queda como formato externo distinto. No se cambia
retroactivamente ningun contrato por esta seccion.

### 5. Importacion privada frente a admision al banco publico

- **Ensayo personal:** el estudiante importa el paquete y PAESSED valida
  esquema, referencias, recursos y estados; puede utilizarlo privadamente
  respetando la procedencia y advirtiendo o restringiendo respuestas no
  verificadas. Importar no concede permiso para distribuir el ensayo.
- **Banco publico:** una barrera cerrada por defecto exige aprobaciones
  validas de fidelidad, contenido educativo y derechos para el uso preciso,
  todas vinculadas a la version y evidencia concretas. Cambios o revocaciones
  invalidan la admision. Esta barrera aun NO esta implementada.

### 6. Decisiones por cerrar

El estado implementado está resumido al principio de esta guía. La visión
anterior no acredita componentes adicionales.

**Pendientes de diseño/prueba:** elegir mecanismo de sesiones aisladas de
AGY; cantidad de lotes en paralelo; politica concreta de escalamiento y
control de tokens; validacion matematica sin solucionario; esquema versionado
de `final.json` y empaquetado de imagenes; `exam.json` heredado; modalidad
del chat; permisos de contenido; autenticacion/aprobaciones para el banco.

El registro de [decisiones](DECISIONS.md) conserva los acuerdos. El
[historial técnico](historial/IMPORTADOR_2026-09.md) conserva las evaluaciones
anteriores. Esta guía reúne Arquitectura y Scanner sin convertir propuestas
en funcionalidades implementadas.
