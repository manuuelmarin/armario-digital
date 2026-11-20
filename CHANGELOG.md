# Changelog

## 2026-11-20 — auditoría de la migración

- El catálogo lee las miniaturas cuando entran en pantalla. Un formulario basado en una revisión antigua vuelve a mostrar los datos confirmados y explica cómo reintentar.
- Se recupera una copia diaria vacía tras una escritura interrumpida. La aplicación identifica una copia dañada con contenido para poder apartarla y crear otra.
- Se validan el orden de las fechas de viaje y las series de la previsión. La última previsión válida sigue disponible si el servicio devuelve fechas imposibles o series incompletas.
- Se comprueba una actualización de la aplicación mientras se edita una prenda y su reapertura y edición sin red. [Matriz de pruebas y mediciones](docs/MIGRACION_PAGES.md)

## 2026-11-19 — cliente web y carpeta local

- Distribución en GitHub Pages con flujos manuales de inventario, outfits, maletas y organización.
- Carpeta local con dos revisiones verificadas de SQLite, imágenes, exportación y restauración de ZIP compatibles con Python.
- Aplicación instalable con caché de recursos y actualización coordinada entre pestañas. [Migración y pruebas](docs/MIGRACION_PAGES.md)

## 0.3.1 — 2026-10-31 — auditoría de integridad y recomendaciones

- Corrige sustituciones que podían quitar una chaqueta/accesorio opcional o convertir una pieza única en dos. Las alternativas conservan su capa y las demás prendas; el generador mantiene los controles del outfit guardado incluso sin JavaScript.
- Vincula cada aprobación a un identificador único y las capturas de recomendación a su versión, evitando aceptar propuestas antiguas tras reutilizar un ID de prenda. Las propuestas anteriores requieren regeneración explícita; prendas, descripciones aprobadas y outfits guardados se conservan.
- Comprueba bytes reales de fotografías al ejecutar, publicar y guardar resultados, y al aprobar descripciones. Recodifica transparencias sobre fondo claro para que prendas oscuras no desaparezcan en visión.
- Valida tablas, columnas y ajustes obligatorios según las migraciones al arrancar, crear, verificar y restaurar copias. Rechaza metadatos de formato/esquema con tipos incorrectos.
- Impide atribuir instrucciones nuevas a tareas con otra versión registrada. Mantiene esquema SQLite 9 y formatos de copia compatibles.
- Auditoría completa y evidencia en [informe 0.3.1](docs/audits/2026-10-31-project.md); 114 pruebas aprobadas localmente, incluidas siete de navegador, y análisis de las 28 dependencias fijadas sin vulnerabilidades conocidas en la consulta realizada. No se han ejecutado modelos reales.

## 0.3.0 — 2026-10-31 — asistencia local opcional

- Dos modelos locales independientes mediante Ollama: Qwen3-VL 4B Instruct Q4 para visión y Qwen3 4B Instruct 2507 Q4 para evaluar outfits a partir de descripciones revisadas.
- Narrativa y siete grupos editables sin duplicar identificación/función, aprobación explícita, revisiones y detección de fotografías o resultados caducados.
- Generación recomendada y sorpresa entre candidatos valorados, prendas fijadas, filtros de ubicación/chaqueta/largo/accesorios, ocasión/estilo y sustitución de una pieza conservando las demás.
- Cola persistente de un trabajador, análisis por lotes, pausa, cancelación, reintento explícito y recuperación de tareas interrumpidas. El armario sigue disponible durante la inferencia.
- Validación estricta de salida e identidad, endpoint loopback fijo y ausencia de descarga o fallback cloud. Desactivado por defecto; creación manual conservada.
- Migración 9 con copia previa y procedencia de descripciones/outfits; compatibilidad con copias de esquemas 1 a 9.
- Guía de preparación, límites y registro de generación del cambio en [IA local](docs/LOCAL_AI.md) y [registro de revisión](docs/changes/2026-10-31-local-ai.md). La calidad y velocidad de modelos reales requieren validación independiente; los tests automatizados usan dobles.

## Sin publicar — organización y fotos

- Edición en lote de categoría y adición de temporada o etiqueta; paginación progresiva del selector conservando la selección.
- Vista previa local de fotos importadas y ordenación de fotografías secundarias. Migración 8 con copia previa y compatibilidad de recuperación.

## Sin publicar — flujos cotidianos

- Importación con nombres editables, edición de categoría en lote y filtros preservados al marcar favoritos.
- Revisión previa de traslados, contador de selección en outfits y maletas, y prendas pendientes en maletas.
- Confirmación de eliminación de fotografías sin JavaScript y verificación de copias guardadas desde Ajustes.

## Sin publicar — documentación del repositorio

- Entrada con estado, esquema, mapa del sistema y estructura del repositorio.
- Índice de guías y contribución en español.
- Arquitectura y primeros pasos ampliados para organización, tableros, importación y tiempo opcional.
- Guía de pruebas corregida: inventario reproducible, evidencia histórica y límites de validación explícitos.
- Decisión de mantener Python; sin cambios de ejecución, esquema ni formatos de copias.

## En desarrollo

- Añade importación por lotes, colecciones, etiquetas y filtros combinables.
- Añade tableros privados con imágenes locales, enlaces y collage con posiciones editables y arrastre.
- Añade consulta manual opcional de previsión meteorológica y caché local.
- Guarda huellas persistentes de las imágenes, verifica las copias y permite limpiar copias diarias tras confirmar y verificar las conservadas.
- Ajusta el límite del servidor para permitir el tamaño de petición anunciado.

- Selección de fotografía principal para el catálogo, los outfits y las maletas.
- Migración con copia previa para preservar los armarios existentes.

## Unreleased

- Add outfit detail, search, favorites filter and safe duplication.
- Duplicate trip lists, prepare a return list without moving garments, and print lists.

- Allow six photographs of up to 10 MiB each in the same request.
- Restrict image decoders before opening uploads and update Pillow.
- Validate backup images and verify the generated archive before reporting success.
- Restore a valid backup while preserving a damaged previous data directory.

## 0.2.0 — 2026-10-29

### Added

- First-run setup with user-defined spaces and no preloaded inventory.
- An isolated, temporary demo with original garment illustrations.
- Responsive images, a 1,024 px preview and a master up to 4,096 px, plus a photo viewer.
- Inventory sorting, filter-preserving location tabs and searchable garment selectors.
- A local typography system, design tokens and responsive layouts across the product.
- Product screenshots, contribution guidelines, security boundaries and a publication guide.

### Changed

- Replaced development-specific defaults and conversation-oriented documentation with reusable product configuration and guides.
- Preserved existing inventory records during schema upgrades; extended backup compatibility to image previews.
- Reduced outfit-list database queries and kept bulk actions contextual to a selection.
- Collapsed advanced filters on small screens and improved form labels and keyboard focus.

## 0.1.0 — 2026-10-29

Initial preview: inventory, local photographs, locations, outfits, packing lists, SQLite migrations and recoverable backups.
