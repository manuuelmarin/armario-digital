# Modelo de datos

Esquema actual: `PRAGMA user_version = 2`. Migraciones SQL incrementales, con transacción e integridad referencial comprobada. `001_core` crea inventario/outfits; `002_trips` añade viajes sin reconstruir tablas existentes.

| Tabla | Papel y relaciones |
|---|---|
| locations | Ubicaciones editables; su borrado se restringe si conservan referencias |
| categories | Catálogo ampliable de categorías |
| garments | Una fila por artículo físico, con identidad estable, ubicación actual y categoría |
| garment_seasons | Relación muchos a muchos limitada a las cuatro temporadas |
| garment_images | Hasta seis fotos por prenda en la aplicación; rutas UUID y hash de entrada, único por prenda |
| garment_movements | Origen, destino, motivo y fecha UTC de los cambios reales de ubicación |
| outfits | Nombre, ocasión, notas y favorito |
| outfit_items | Asociación única outfit/prenda; restringe borrar una prenda usada |
| trips | Origen, destino, fechas opcionales y notas; valida orden cronológico |
| trip_items | Una prenda única por viaje o un objeto libre; indicador de preparado |

Los precios se almacenan en céntimos enteros y se introducen en euros. Las fechas de compra y viaje son fechas ISO sin hora. Los eventos usan fecha/hora UTC. Los campos opcionales de texto utilizan cadena vacía; las fechas y precios desconocidos usan NULL.

Los outfits y las maletas referencian prendas, sin copiar su ubicación ni duplicar fotos. Al mover una prenda, todas las vistas muestran su ubicación actual. Importar un outfit en una maleta guarda sus prendas como lista independiente: cambiar o eliminar después el outfit no cambia esa maleta.

Se utiliza `ON DELETE RESTRICT` en referencias a prendas y ubicaciones que protegen información de uso; `CASCADE` en las filas dependientes propias de una prenda, outfit o viaje. Archivar no borra filas. Las ubicaciones con historial se pueden renombrar, pero no borrar: los eventos seguirán usando su identidad y mostrarán su nombre actual.

Las imágenes se recodifican a WebP (máximo 2.400 px por lado) y miniaturas de 560 px. No se conserva el original binario ni su EXIF. La primera foto que queda según ID es la principal. Se rechazan más de 10 MB por foto, más de 24 megapíxeles y formatos distintos de JPEG/PNG/WebP. No se admiten HEIC o SVG.

Un fallo antes del commit retira los archivos recién creados. Un cierre abrupto entre operaciones de disco y SQL podría dejar archivos huérfanos, que no se sirven por referencia en la interfaz ni se incluyen en copias. Se prioriza no borrar imágenes referenciadas; no se ejecuta limpieza automática destructiva.
