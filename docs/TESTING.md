# Pruebas y evidencia de verificación

Para la versión de GitHub Pages consulta [uso e importación en Windows](WINDOWS_PAGES.md) y [arquitectura, pruebas y despliegue](MIGRACION_PAGES.md).

## Referencia de la aplicación Python

Estado auditado en 0.3.1: **114 pruebas locales aprobadas**, incluidas siete de navegador. El [informe](audits/2026-10-31-project.md) detalla los seis problemas encontrados, sus reproducciones, correcciones, cobertura y límites. `tests/test_project_audit.py` conserva las regresiones; `test_browser.py` comprueba además la sustitución de una pieza de un outfit con chaqueta y accesorio sin JavaScript.

## Comandos reproducibles

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m djlint armario/templates --check
```

La suite normal omite los recorridos de navegador mediante `RUN_BROWSER_TESTS`. Consulta el inventario del checkout actual; los recuentos históricos no son una garantía de cobertura:

```bash
python -m pytest --collect-only -q
python -m pytest tests/test_browser.py --collect-only -q
```

Para incluir los recorridos:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
$env:RUN_BROWSER_TESTS="1"
.venv\Scripts\python.exe -m pytest -q
```

En Linux, usa `RUN_BROWSER_TESTS=1 python -m pytest -q`. `BROWSER_EXECUTABLE` permite indicar un Chromium local; no es un requisito de la aplicación. Las capturas se guardan en `test-results/`, excluido de Git. Para explorar o capturar una colección ficticia, usa `python run.py --demo`.

## Áreas verificadas

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

## Organización, inspiración y copias

Los módulos `test_organization.py` y `test_boards_weather.py` cubren asociaciones y filtros, relaciones archivadas, imágenes de tableros y copias, enlaces inválidos, posiciones de muchos elementos, caché meteorológica con proveedor simulado y limpieza de copias. Los casos de inventario y copias incluyen la reversión de lotes y la detección de imágenes modificadas.

La suite de navegador incorpora el recorrido de organización, tablero e importación. Parte de sus capturas usa carpetas temporales de pytest; conserva la evidencia que necesites antes de eliminarlas. Las capturas indicadas por `ARMARIO_SCREENSHOTS` corresponden a los recorridos que utilizan esa variable.

## Revisar un cambio

1. Ejecuta los casos afectados y las comprobaciones de formato del repositorio.
2. Ejecuta la suite completa cuando cambien contratos compartidos, persistencia o recuperación.
3. Para cambios de interfaz, ejecuta los recorridos de navegador e inspecciona escritorio y móvil, carga de imágenes, foco y desbordamientos.
4. En cambios de datos, comprueba relaciones pobladas, reversión de errores y restauración; contar filas no basta.
5. Registra commit, comandos, plataforma y resultados, incluidas omisiones y fallos. Distingue un fallo de arranque del navegador de una aserción fallida de la aplicación.

No elimines pruebas por similitud de título: compara entradas, aserciones, efectos y capa antes de considerar redundante un caso. Las respuestas simuladas del tiempo validan el contrato y la recuperación ante errores; no demuestran disponibilidad del proveedor real.

## Evidencia histórica y límites

### Asistencia local (0.3)

`tests/test_local_ai.py` verifica revisión manual, dos llamadas independientes de visión/texto, filtros, prendas fijadas, sustitución, rechazo de resultados caducados, cambios de foto/revisión/archivo/ubicación/borrado, integridad, concurrencia, pausa/cancelación/reinicio y migración/recuperación. `tests/test_ai_protocol.py` usa HTTP real contra un doble en loopback para comprobar el contrato, límites, redirecciones, respuesta incompleta y ausencia de descarga/fallback. No ejecutan pesos de modelos ni predicen calidad o velocidad.

El recorrido de navegador de asistencia verifica siete grupos, revisión y generación con una respuesta simulada, guardado de outfit, formularios sin JavaScript, imágenes y desbordamiento a 1.440 y 390 px. El [registro del cambio](changes/2026-10-31-local-ai.md) conserva el resultado concreto de la revisión. La prueba de modelos reales en un equipo de 32 GB queda descrita en [LOCAL_AI.md](LOCAL_AI.md).

Verificación local del 29 de octubre de 2026: **39 pruebas aprobadas en aquella revisión**, incluidas las tres de navegador. Ruff y el formato de plantillas pasan sin incidencias. Se utiliza Linux, Python 3.12.14, SQLite 3.53.1 y Chromium 153. El Chromium local procede de una herramienta temporal de QA externa al proyecto; CI usa la instalación estándar de Playwright.

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

## Evidencia de la ampliación del esquema 7

En la revisión previa de las funcionalidades integradas en la PR #5 se registraron 53 pruebas locales aprobadas y cuatro recorridos de navegador omitidos, además de Ruff y djLint aprobados. La reejecución local con navegador no pudo completarse porque Chromium fallaba al arrancar. No se presenta esa reejecución como aprobada. Las comprobaciones finales de GitHub de aquella PR fueron satisfactorias en Windows y Linux.

Estos resultados son históricos. Para evaluar una revisión nueva, consulta su ejecución de CI y genera el inventario actual con los comandos anteriores. La consulta real a Open-Meteo, el instalador interactivo de Windows y los fallos físicos de disco requieren validación independiente.
