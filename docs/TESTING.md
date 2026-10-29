# Verificación — 0.2.0

## Comandos reproducibles

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m djlint armario/templates --check
```

La suite normal ejecuta 36 casos y omite tres recorridos de navegador. Para incluirlos:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
$env:RUN_BROWSER_TESTS="1"
.venv\Scripts\python.exe -m pytest -q
```

En Linux, usa `RUN_BROWSER_TESTS=1 python -m pytest -q`. `BROWSER_EXECUTABLE` permite indicar un Chromium local; no es un requisito de la aplicación. Las capturas se guardan en `test-results/`, excluido de Git. Para explorar o capturar una colección ficticia, usa `python run.py --demo`.

## Cobertura

- Inventario: alta, edición, archivo, favoritos, temporadas, precios, búsqueda con tildes, filtros combinados, ordenación validada y paginación.
- Primer uso: instalación sin espacios ni prendas; creación del primer espacio desde móvil y alta de una prenda.
- Fotografías: validación y límites, deduplicación, orientación EXIF, eliminación de metadatos, tres resoluciones sin ampliación artificial y retirada de archivos tras un fallo.
- Traslados: operaciones masivas atómicas, historial y conservación de outfits. Eliminación restringida de prendas en uso.
- Outfits: prendas archivadas ya asociadas, bloqueo de nuevas incorporaciones archivadas y selección buscable que conserva la selección al filtrar.
- Maletas: importación sin duplicados, objetos generales, preparación independiente del traslado y confirmación de llegada sin duplicar movimientos.
- Recuperación: snapshot, descarga, hashes, restauración de fotos y relaciones, conservación del estado previo y rechazo de ZIP manipulados, rutas ajenas y esquemas futuros.
- Migraciones: bases pobladas de esquemas anteriores, fotos sin preview, espacios y asociaciones existentes; copia previa recuperable.
- Seguridad local: CSRF, origen de escrituras, Host permitido, escape HTML, rutas de fotografías y exclusión de procesos simultáneos.
- Navegador: recorrido completo con dos fotografías, galería, traslado, outfit, viaje, preparación, llegada y descarga de copia; primer uso; demo, selección de imagen en DPR 2 y filtros móviles.
- Adaptación: nueve pantallas a 1.440, 850 y 390 px sin desbordamiento horizontal; errores de JavaScript vigilados durante el recorrido completo.

## Resultado y límites

Verificación local del 29 de octubre de 2026: **39 pruebas aprobadas**, incluidas las tres de navegador. Ruff y el formato de plantillas pasan sin incidencias. Se utiliza Linux, Python 3.12.14, SQLite 3.53.1 y Chromium 153. El Chromium local procede de una herramienta temporal de QA externa al proyecto; CI usa la instalación estándar de Playwright.

Se revisan ocho pantallas con axe-core, a 1.600 y 390 px, para las reglas WCAG A/AA 2.0 y 2.1. Resultado: cero incidencias automáticas en las 16 vistas y ningún desbordamiento horizontal. La comprobación automática se complementa con revisión visual de escritorio y móvil. No equivale a una certificación ni sustituye una prueba con lector de pantalla.

CI ejecuta dependencias, Ruff, formato de plantillas y pruebas de servidor en Windows y Linux. Linux añade los recorridos de Chromium. El lanzador `.cmd` y la instalación interactiva requieren comprobación manual en Windows; una ejecución de CI no valida esa experiencia. macOS no forma parte de la matriz actual.

No se han probado HEIC, fallos físicos de disco ni carga multiusuario. La aplicación es local y monousuario. La selección de prendas para outfits y maletas todavía renderiza la colección activa completa.

## Medición sintética

Comando: `python -m tests.benchmark`. Genera inventarios temporales con imágenes sintéticas pequeñas. Tras un calentamiento se realizan 30 solicitudes por ruta con el cliente Flask. La galería devuelve 48 tarjetas; datos y fotos se eliminan al finalizar.

| Prendas | Galería mediana / p95 (ms) | Filtros combinados mediana / p95 (ms) |
|---:|---:|---:|
| 100 | 5,18 / 8,80 | 4,20 / 5,31 |
| 500 | 4,91 / 6,26 | 5,78 / 7,21 |
| 1.000 | 4,66 / 5,87 | 5,88 / 6,63 |

Medición de consulta y render HTML en el entorno local indicado. No incluye red, decodificación de fotografías ni pintado del navegador y no predice tiempos en otros equipos.
