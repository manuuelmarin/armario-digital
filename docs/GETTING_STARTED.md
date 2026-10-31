# Primeros pasos

## Crear un inventario

Una instalación nueva empieza vacía. Abre la aplicación, crea un espacio con el nombre que tenga sentido para la colección y añade una prenda. Nombre, categoría y espacio son obligatorios; la fotografía y los demás detalles se pueden completar después.

Los espacios pueden representar armarios, habitaciones o lugares. Se crean y renombran desde Ubicaciones. No hay ciudades ni ubicaciones fijadas en el código. Renombrar un espacio conserva los artículos y los movimientos asociados.

## Explorar y combinar

Busca por nombre, marca, color o notas. Los filtros de categoría, temporada, espacio y favoritos se pueden combinar; cambiar de espacio mediante las pestañas conserva los demás filtros. En pantallas pequeñas, el botón Filtros despliega las opciones avanzadas.

Abre una ficha para consultar detalles, ver sus fotografías ampliadas o recorrer las imágenes. Los outfits reúnen prendas de cualquier espacio y muestran dónde se encuentran. El selector de prendas admite búsqueda local sin perder la selección.

## Preparar un viaje

Crea al menos dos espacios para definir origen y destino. Añade prendas o importa un outfit: las repetidas aparecen una sola vez. También se pueden incluir objetos como documentación o un neceser.

Marcar un elemento como preparado no cambia su ubicación. Cuando las prendas hayan llegado, usa Revisar traslado a destino y confirma la selección. La operación no mueve prendas archivadas ni artículos situados en un tercer espacio.

## Guardar y recuperar

Los cambios se guardan al enviar los formularios y permanecen al cerrar. Archivar una prenda conserva outfits y maletas. La eliminación definitiva se bloquea mientras existan referencias que la utilicen.

Crea una copia desde Ajustes antes de actualizaciones o cambios importantes. Conserva otra copia fuera del equipo. El procedimiento de verificación y recuperación está en [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## Probar sin un inventario real

`python run.py --demo` abre una colección ficticia en una carpeta temporal. Todas las ilustraciones se generan desde código original y no representan artículos poseídos por una persona real. Al cerrar se elimina la carpeta de demo. Para usarla al mismo tiempo que un inventario habitual, elige otro puerto con `--port`.

## Organizar e importar

En Colecciones puedes reunir prendas sin cambiar su espacio; las etiquetas permiten filtros adicionales en el inventario. Archivar una prenda conserva las asociaciones existentes. Eliminar una agrupación elimina su relación, no las prendas.

La importación por lotes crea una prenda por fotografía con categoría y espacio comunes. Revisa después nombres y detalles. Admite hasta 20 imágenes, 10 MiB por archivo y 64 MiB por petición, incluido el contenido del formulario. Si falla un archivo, el lote se revierte completo; corrige el problema antes de repetirlo.

## Inspiración y tiempo

Crea un tablero en Inspiración y añade imágenes, notas o enlaces HTTP/HTTPS. Ajusta posición y anchura con los campos del formulario; también puedes arrastrar si tienes JavaScript. Los cambios enviados se guardan localmente. El collage no tiene exportación a imagen.

En Tiempo, introduce unas coordenadas y un nombre reconocible. Solo Actualizar consulta al proveedor; la pantalla muestra la última previsión guardada y su fecha. Las coordenadas y la IP se envían a Open-Meteo al solicitarla. Si falla la conexión, se conserva el resultado anterior: revisa su antigüedad antes de utilizarlo.

## Actualizar sin perder el inventario

1. Crea una copia desde Ajustes y conserva otra fuera del equipo.
2. Cierra el servidor con `Ctrl+C` antes de sustituir archivos.
3. Actualiza la carpeta de código completa e instala sus requisitos; en Windows puedes volver a usar `instalar.cmd`.
4. Arranca con la misma carpeta de datos y comprueba espacios, prendas y fotografías.

Si algo falla, conserva el mensaje de error sin datos personales y consulta [recuperación](BACKUP_RESTORE.md). No borres la carpeta de datos ni intentes abrir simultáneamente dos versiones contra el mismo inventario. La demo temporal no sirve para conservar una colección real.
