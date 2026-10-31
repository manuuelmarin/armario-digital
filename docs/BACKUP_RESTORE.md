# Copias y restauración

## Crear y conservar

Con la aplicación abierta: **Ajustes → Crear y descargar copia**. Con ella cerrada:

```powershell
.venv\Scripts\python.exe run.py backup
```

Cada ZIP incluye `wardrobe.sqlite`, exactamente sus imágenes referenciadas (master, preview y miniatura cuando existan) y `manifest.json` con esquema, fecha y hashes SHA-256. Incluye imágenes de prendas y tableros, y la última previsión guardada en SQLite. No incluye entornos, secretos de sesión ni copias anteriores. Se usa `sqlite3.Connection.backup`, no una copia ciega del archivo abierto. Las mutaciones de la app quedan bloqueadas durante el snapshot y el empaquetado de fotos.

Desde el esquema 5, las huellas persistentes se comparan con cada imagen antes de crear una copia y durante su verificación. La primera huella de imágenes antiguas se establece al migrar: no permite detectar cambios anteriores. La limpieza de copias diarias es manual, conserva las manuales y las previas a migraciones y verifica las copias que se van a mantener antes de borrar las antiguas.

La copia se escribe con extensión temporal y se renombra solo si termina. Una imagen referenciada ausente hace fallar la copia; no se entrega un archivo aparentemente completo. Las copias manuales se conservan en `DATA_DIR/backups`, además de la descarga elegida por el navegador.

Se crea una copia al primer arranque de cada día UTC y antes de migrar datos existentes. **No es un temporizador**: si dejas el proceso abierto varios días, crea una copia manual de los cambios importantes. No hay retención automática en 0.2; revisa espacio y conserva copias en otro dispositivo. Una copia guardada solo en el mismo disco no cubre la pérdida de ese disco.

## Verificar sin restaurar

```powershell
.venv\Scripts\python.exe run.py verify "C:\Copias\armario.zip"
```

Verifica ZIP, nombres permitidos, hashes, versión, integridad SQLite, relaciones y decodificación de imágenes. La creación verifica el archivo completo antes de darlo por terminado. Rechaza entradas duplicadas, enlaces simbólicos, rutas ajenas al formato, más de 20.002 archivos o más de 4 GB descomprimidos. Las copias están sin cifrar: guárdalas con el mismo cuidado que tus fotos.

Desde 0.3.1 se comprueban también tablas/columnas obligatorias derivadas de las migraciones y la fila de ajustes del esquema 9. La ausencia de una tabla no se considera válida por el mero resultado `ok` del chequeo mecánico de SQLite. El manifiesto requiere enteros para formato y esquema. Esta validación se aplica antes de sustituir los datos al restaurar y también en el arranque; no modifica el formato ni elimina la compatibilidad de esquemas 1–9.

## Restaurar

1. Cierra Armario Digital con Ctrl+C.
2. Ejecuta `verify` y comprueba el número de prendas y outfits.
3. Ejecuta:

```powershell
.venv\Scripts\python.exe run.py restore "C:\Copias\armario.zip" --confirm
```

Sin `--confirm`, el comando verifica y describe el contenido sin cambiar los datos. Para una carpeta distinta, coloca la opción global antes de `restore`:

```powershell
.venv\Scripts\python.exe run.py --data-dir "D:\MiArmario" restore "C:\Copias\armario.zip" --confirm
```

La restauración adquiere el bloqueo de instancia. Si el servidor sigue abierto, se rechaza. Se extrae y verifica en una carpeta temporal del mismo directorio padre. Cuando el estado actual lo permite, se realiza una copia adicional; también se conserva su carpeta entera con sufijo `-before-restore-…`. Solo entonces se sustituye la carpeta activa por la verificada. Si falla el segundo renombrado, se intenta devolver la carpeta anterior a su sitio.

Una interrupción física entre ambos renombrados puede dejar los datos en la carpeta `-before-restore-…`: no se han borrado. Con la aplicación cerrada, renombra esa carpeta al nombre original antes de volver a arrancar. No elimines la carpeta anterior hasta revisar el inventario recuperado y descargar otra copia. El diseño no garantiza recuperación frente a cualquier fallo de hardware o corrupción del sistema de archivos.

La versión 0.3 acepta copias de esquemas 1 a 9, incluidas fotos antiguas sin preview; el siguiente arranque los migra con copia previa. Se rechazan versiones futuras para impedir que código antiguo interprete datos que desconoce.

Desde el esquema 9 también se guardan perfiles revisados, tareas y procedencia de outfits asistidos. No se guardan los pesos ni la configuración de Ollama: prepara el servicio por separado en el equipo de destino. Las tareas en cola pueden continuar al arrancar si la asistencia estaba activa y sin pausa; las interrumpidas en curso pasan a error y requieren reintento explícito. Consulta [IA local](LOCAL_AI.md) antes de reanudar una cola restaurada.

Si la base de datos o alguna imagen del estado actual está dañada, la restauración conserva la carpeta anterior completa aunque no pueda generar una copia adicional. Revisa esa carpeta antes de eliminarla.
