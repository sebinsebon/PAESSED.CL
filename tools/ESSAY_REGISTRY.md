# Registro local de ensayos

`Ensayos/` vive fuera del repositorio Git `PAESSED.CL/`. El registro, los PDFs,
los solucionarios y los baselines archivados son material local. El script solo
calcula hashes de PDFs; no extrae ni interpreta sus paginas.

Desde `PAESSED.CL/`, usar `python tools/essay_registry.py --root ..\Ensayos`.

1. `inventory` enumera `nuevos/` y distingue hashes ya usados, selecciones
   preparadas, candidatos virgenes y solucionarios registrados.
2. Antes de la primera corrida, preparar un JSON con exactamente ocho casos
   distintos y `evaluation_criteria` no vacio. `prepare --pdf RUTA --cases RUTA
   --type holdout-stage1 --origin ORIGEN` muestra la simulacion. Repetir con
   `--apply` para congelar el hash del PDF y de la seleccion.
3. Conservar los resultados iniciales y un `run_execution.json` con `started_at`
   en formato ISO 8601 con zona horaria. `finalize --pdf RUTA --cases RUTA
   --results RUTA --execution RUTA` simula. Con `--apply`, archiva copias
   verificadas de casos, resultados y ejecucion en `Ensayos/baselines/<SHA-256>/`,
   registra el primer uso y mueve el PDF a `usados/` sin sobrescribir.
4. `move-used --pdf RUTA` simula el movimiento de una copia cuyo hash ya tiene
   uso registrado. `--apply` conserva la subcarpeta relativa. Los solucionarios
   no se mueven con este comando.
5. `register-solutionario --pdf RUTA --reason TEXTO` registra material de apoyo
   aparte. Puede recibir `--possible-sha256 HASH` repetido; la asociacion
   permanece sin confirmar. Tambien requiere `--apply` para guardar.
6. `backup-registry` simula una copia privada de `registro.json`. Con `--apply`
   escribe una copia verificada por SHA-256 en `Ensayos/respaldos/`. Cada cambio
   posterior del registro crea automaticamente un respaldo de la version previa.
7. `recover` simula la reconciliacion de un movimiento interrumpido. Verifica
   el hash en ambas ubicaciones antes de completar el movimiento, retirar una
   copia identica o actualizar el registro. Repetir con `--apply` solo despues
   de revisar la simulacion.

Todos los comandos que cambian archivos simulan por defecto. Una coincidencia
de SHA-256 impide reutilizar un ensayo como virgen incluso si el nombre cambia.
Un destino existente detiene un movimiento nuevo. Si falla despues de registrar
el uso, `move_pending` y el hash conservan el bloqueo de reutilizacion; usar
`recover` antes de intentar otra operacion. Si la interrupcion ocurre durante
el archivo del baseline, `finalize` puede repetirse: reutiliza solamente copias
ya verificadas y nunca sobrescribe una copia diferente. El bloqueo del registro
se libera al terminar el proceso, incluso despues de una caida.

Los respaldos quedan fuera de Git junto con los PDFs. Para restaurar uno,
comprobar su SHA-256, conservar una copia del registro actual y reemplazarlo
solo tras revisar el historial y los movimientos pendientes. Un respaldo en el
mismo disco protege frente a ediciones accidentales; para fallos del disco,
copiar `Ensayos/` a un medio privado o cifrado fuera del repositorio.

En el historial migrado, `used_at` y `initial_results` son `null` cuando los
artefactos existentes no acreditan esos datos. Las rutas originales se
conservan en `original_locations` aunque una copia pase a `usados/`.
