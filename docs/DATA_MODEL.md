# Modelo de datos

Esquema actual: `PRAGMA user_version = 9`. Las migraciones se aplican secuencialmente dentro de transacciones, con verificación de claves foráneas y copia previa de datos existentes.

| Tabla | Función |
|---|---|
| `locations` | Espacios configurables; eliminación restringida si conservan referencias |
| `categories` | Categorías de prendas ampliables |
| `garments` | Artículo físico, categoría, ubicación actual y metadatos |
| `garment_seasons` | Temporadas múltiples por artículo |
| `garment_images` | Archivos de imagen, hash y dimensiones; portada elegida o, por defecto, orden de ID |
| `garment_movements` | Origen, destino, motivo y fecha de cambios reales |
| `outfits`, `outfit_items` | Combinaciones y asociaciones únicas con prendas |
| `trips`, `trip_items` | Viajes, prendas deduplicadas, objetos libres y preparación |
| `image_integrity` | Huellas SHA-256 persistentes de las imágenes aceptadas |
| `collections`, `collection_items` | Agrupaciones de prendas sin cambiar su ubicación |
| `tags`, `garment_tags` | Etiquetas asociadas a prendas |
| `boards`, `board_items` | Ideas, imágenes, enlaces y geometría del collage |
| `weather_cache` | Última previsión consultada explícitamente |
| `ai_settings` | Activación y pausa de asistencia local; desactivada por defecto |
| `garment_profiles` | Descripción aprobada con siete grupos, revisión, foto/hash y procedencia; cascada al eliminar prenda |
| `ai_jobs` | Cola persistente, solicitud normalizada, versiones, resultado validado y estado; no guarda payloads de imágenes |
| `outfit_origins` | Procedencia y valoraciones originales de outfits asistidos; se retira al editarlos manualmente |

Los precios se almacenan en céntimos y se introducen en euros. Las fechas de compra y viaje son ISO sin hora; los eventos se registran en UTC. Las prendas no se duplican al incorporarlas a un outfit o viaje.

## Imágenes

Cada imagen nueva tiene un master WebP de hasta 4.096 px, una vista previa de hasta 1.024 px y una miniatura de hasta 512 px. Las dimensiones reales se almacenan para construir un `srcset` válido, sin inventar resolución ni ampliar fotografías pequeñas. El master conserva más detalle que las variantes de navegación, pero sigue siendo una versión recodificada; el archivo original y su EXIF no se conservan.

Se admiten JPEG, PNG y WebP, hasta 10 MB y 24 megapíxeles por archivo; hasta seis imágenes por prenda. Los nombres internos son UUID, no rutas elegidas por el cliente. Los archivos nuevos se retiran si falla la transacción. Una interrupción de proceso podría dejar archivos huérfanos, que no se incluyen en copias; no se hace limpieza destructiva automática.

## Evolución

- `001_core`: esquema de inventario y outfits. La definición de instalación nueva ya no contiene datos de un entorno de desarrollo; la estructura no se altera.
- `002_trips`: listas de viaje.
- `003_responsive_images`: añade vistas previas y dimensiones opcionales, con índices de referencias inversas. No reconstruye tablas ni borra registros.

- `004_primary_image`: elección de portada sin alterar la ordenación original por defecto.
- `005_image_integrity`: crea una huella de los archivos existentes tras la copia previa; no puede detectar una alteración anterior a esa primera huella.
- `006_organization`: colecciones y etiquetas con relaciones a prendas.
- `007_boards_weather`: tableros y última consulta meteorológica.

Las bases de datos existentes conservan sus espacios y prendas. Las fotografías antiguas pueden tener `preview` y dimensiones a NULL; la interfaz y las copias soportan esa situación. Se aceptan copias de esquemas compatibles del 1 al 9.

La migración 8 conserva las fotografías existentes y añade su orden en la galería. La imagen principal sigue mostrándose primero. Las copias anteriores se migran tras verificar y conservar un respaldo previo.

La migración 9 añade la asistencia sin alterar prendas, fotos ni asociaciones existentes. El perfil estructurado tiene versión 1 y las instrucciones iniciales `wardrobe-1`. Los resultados visuales son propuestas en `ai_jobs`: no se convierten en `garment_profiles` hasta aprobarlos. Cada aprobación aumenta la revisión, compara la fuente y conserva procedencia. Una foto principal distinta vuelve caducado el perfil anterior. Los resultados textuales se comprueban contra el snapshot y contra los datos actuales antes de guardarse.

Estados de tarea: `queued`, `running`, `completed`, `failed`, `cancelled`, `stale`. El reinicio convierte trabajos interrumpidos `running` en `failed`; no los repite sin acción del usuario. Las tareas en cola y la pausa persisten y se incluyen en las copias, igual que los perfiles aprobados. Borrar una prenda elimina su perfil y deja sin referencia de prenda el historial; borrarlo explícitamente desde tareas elimina también sus snapshots, sin modificar outfits ni revisiones aprobadas. Las copias anteriores pueden conservar ese historial.

En 0.3.1 las capturas internas de recomendación usan `version=2` y la procedencia de cada nueva aprobación incorpora un UUID `approval_id`. La huella incluye esa procedencia para impedir que reutilizar un ID SQLite vuelva válida una generación de una prenda eliminada. El perfil sigue en versión 1 y no cambia el esquema SQL. Los perfiles anteriores son legibles; las propuestas del formato anterior requieren regeneración explícita. La integridad de la fuente se contrasta también con el archivo real al ejecutar, publicar, aprobar y guardar.
