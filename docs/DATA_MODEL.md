# Modelo de datos

Esquema actual: `PRAGMA user_version = 7`. Las migraciones se aplican secuencialmente dentro de transacciones, con verificación de claves foráneas y copia previa de datos existentes.

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

Las bases de datos existentes conservan sus espacios y prendas. Las fotografías antiguas pueden tener `preview` y dimensiones a NULL; la interfaz y las copias soportan esa situación. Se aceptan copias de esquemas compatibles del 1 al 7.
