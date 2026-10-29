# Verificación de la versión 0.1

## Comandos reproducibles

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

La suite normal incluye 29 casos y omite explícitamente la prueba de navegador. Para ejecutarla:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
$env:RUN_BROWSER_TESTS="1"
.venv\Scripts\python.exe -m pytest -q
```

En Linux, usa `RUN_BROWSER_TESTS=1 python -m pytest -q`. Se puede indicar un Chromium local con `BROWSER_EXECUTABLE`; no es un requisito de la aplicación. Las capturas de prueba se guardan en `test-results/`, excluido de Git.

## Qué se ha comprobado

- CRUD y archivo, temporadas y precios, búsqueda con tildes, filtros combinados y paginación.
- Fotos inválidas, límites, deduplicación, corrección EXIF, miniaturas y retirada de archivos tras un fallo.
- Traslados masivos atómicos, historial y conservación de outfits. Eliminación restringida de prendas en uso.
- Edición de outfits con prendas archivadas ya asociadas; bloqueo de incorporaciones nuevas de esas prendas.
- Importación deduplicada de outfits a maletas; objetos generales y preparación sin cambios de ubicación.
- Traslado explícito de una selección preparada; exclusión de otras ciudades, selecciones obsoletas y repetición sin duplicar movimientos.
- Snapshot completo, descarga HTTP, verificación y restauración con fotos y relaciones; conservación de datos anteriores.
- Copias manipuladas, rutas ajenas, fotos ausentes, esquema futuro y exclusión de procesos simultáneos.
- Migración de una base v1 poblada a v2 con outfits: se conservan filas y asociaciones y existe una copia previa recuperable.
- CSRF, origen de escrituras, Host no permitido, escape HTML y rutas de fotografías.
- Navegador: alta con fotografía, traslado, outfit, viaje, preparación, llegada y descarga de copia. Nueve pantallas a 1.440, 850 y 390 px, sin errores JavaScript ni desbordamiento horizontal.

La prueba real de navegador detectó y permitió corregir un problema de contexto de macros Jinja que dejaba vacíos los desplegables de ubicación. La revisión visual posterior corrigió el espacio del icono del buscador.

## Entorno y límites

Resultado local final: **30 casos aprobados**, incluida la prueba real de navegador, y comprobaciones de Ruff sin incidencias. También se comprobó el arranque real de Waitress en una ruta con espacios, la creación de la copia diaria y el modo de verificación de restauración sin confirmación.

Verificación local realizada en Linux, Python 3.12.14, SQLite 3.53.1 y Chromium 153. Las descargas estándar de Chromium desde el entorno de trabajo no funcionaron; para la comprobación local se utilizó el binario de `@sparticuz/chromium` del registro npm, solo como herramienta temporal, fuera del proyecto. No se añade a las dependencias de la app. La CI usa la instalación normal de Playwright.

Hay configuración de CI para Linux y Windows. Su ejecución remota y la prueba del instalador `.cmd` en el Windows del propietario deben verificarse por separado; no se equipara una prueba local de servidor con esa validación. No se declara versión estable todavía.

No se ha hecho una auditoría de accesibilidad con lector de pantalla, una prueba con fotos HEIC, un ensayo de caída física de disco ni pruebas de carga multiusuario. No están dentro del alcance de 0.1.

## Medición sintética

Comando: `python -m tests.benchmark`. Se generan inventarios temporales con una imagen WebP sintética pequeña y miniatura por prenda. Tras un calentamiento, se realizan 30 solicitudes por ruta con el cliente de pruebas Flask. La galería devuelve 48 tarjetas. Datos y imágenes se eliminan al finalizar.

| Prendas | Galería mediana / p95 (ms) | Filtros combinados mediana / p95 (ms) |
|---:|---:|---:|
| 100 | 2,97 / 3,82 | 2,63 / 3,45 |
| 500 | 2,98 / 3,61 | 3,55 / 4,42 |
| 1.000 | 2,93 / 3,81 | 3,70 / 4,90 |

Entorno indicado arriba, almacenamiento del espacio de trabajo; se mide consulta y render HTML del servidor. No incluye red, descarga/decodificación de fotografías grandes ni pintado del navegador, y no predice tiempos en el equipo del propietario. La selección de prendas dentro de outfits y maletas todavía no tiene paginación.
