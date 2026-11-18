# Primeros pasos

## Instalar y abrir

### Windows

1. Instala [Python](https://www.python.org/downloads/) 3.11 o posterior con el lanzador `py`.
2. Clona el repositorio o descarga **Code → Download ZIP** y extrae la carpeta completa.
3. Ejecuta `instalar.cmd` para crear el entorno e instalar las dependencias. La primera instalación requiere conexión.
4. Abre `iniciar.cmd`. Si el navegador no se abre, visita `http://127.0.0.1:8765`. Para cerrar el servidor, pulsa `Ctrl+C` en la consola.

### Linux y macOS

Desde la carpeta del proyecto, con Python 3.11 o posterior:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

La integración continua comprueba el servidor en Windows y Linux con Python 3.12. La instalación interactiva en Windows y la compatibilidad con macOS requieren validación manual.

## Probar la demo

Después de instalar, abre PowerShell en la carpeta del proyecto y ejecuta `.\iniciar.cmd --demo`. En Linux o macOS, con el entorno virtual activo, ejecuta `python run.py --demo`.

La demo crea prendas, ilustraciones y espacios ficticios en una carpeta temporal que se elimina al cerrar. Si ya tienes el catálogo abierto, añade `--port 8766` al comando para usar ambos a la vez.

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

La aplicación guarda los datos fuera del código, en `%LOCALAPPDATA%\ArmarioDigital` en Windows y `~/.local/share/armario-digital` en sistemas Unix. Puedes elegir otra carpeta con `--data-dir` o la variable `ARMARIO_DATA_DIR`.

Los cambios se guardan al enviar los formularios y permanecen al cerrar. Archivar una prenda conserva outfits y maletas. La eliminación definitiva se bloquea mientras existan referencias que la utilicen.

Crea una copia desde Ajustes antes de actualizaciones o cambios importantes. Conserva otra copia fuera del equipo. El procedimiento de verificación y recuperación está en [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## Organizar e importar

En Colecciones puedes reunir prendas sin cambiar su espacio; las etiquetas permiten filtros adicionales en el inventario. Archivar una prenda conserva las asociaciones existentes. Eliminar una agrupación elimina su relación, no las prendas.

La importación por lotes crea una prenda por fotografía con categoría y espacio comunes. Puedes revisar y editar los nombres antes de importar; sin JavaScript se utilizan los nombres de archivo. Revisa los demás detalles después. Admite hasta 20 imágenes, 10 MiB por archivo y 64 MiB por petición, incluido el contenido del formulario. Si falla un archivo, el lote se revierte completo; corrige el problema antes de repetirlo.

## Inspiración y tiempo

Crea un tablero en Inspiración y añade imágenes, notas o enlaces HTTP/HTTPS. Ajusta posición y anchura con los campos del formulario; también puedes arrastrar si tienes JavaScript. Los cambios enviados se guardan localmente. El collage no tiene exportación a imagen.

En Tiempo, introduce unas coordenadas y un nombre reconocible. Solo Actualizar consulta al proveedor; la pantalla muestra la última previsión guardada y su fecha. Las coordenadas y la IP se envían a Open-Meteo al solicitarla. Si falla la conexión, se conserva el resultado anterior: revisa su antigüedad antes de utilizarlo.

Selecciona prendas en el inventario para cambiarles la categoría o añadir temporada y etiqueta en lote o revisar un traslado; ninguna ubicación cambia hasta confirmar. En Ajustes puedes verificar una copia guardada sin restaurarla.

## Actualizar sin perder el inventario

1. Crea una copia desde Ajustes y conserva otra fuera del equipo.
2. Cierra el servidor con `Ctrl+C` antes de sustituir archivos.
3. Actualiza la carpeta de código completa e instala sus requisitos; en Windows puedes volver a usar `instalar.cmd`.
4. Arranca con la misma carpeta de datos y comprueba espacios, prendas y fotografías.

Si algo falla, conserva el mensaje de error sin datos personales y consulta [recuperación](BACKUP_RESTORE.md). No borres la carpeta de datos ni intentes abrir simultáneamente dos versiones contra el mismo inventario. La demo temporal no sirve para conservar una colección real.

En la ficha de una prenda, usa las flechas para ordenar las fotografías secundarias; la principal permanece al inicio. Los selectores paginan visualmente con JavaScript y conservan las selecciones entre páginas; sin JavaScript muestran todas las prendas.

## Asistencia local, si decides activarla

Desde **Ajustes → Configurar asistencia local**, prepara Ollama y sus dos modelos siguiendo [LOCAL_AI.md](LOCAL_AI.md). La instalación del catálogo no descarga modelos. Revisa las descripciones desde cada prenda y abre **Outfits → Generar outfits** para fijar piezas y elegir filtros. Cada resultado necesita una acción explícita para guardarse; el armario y los outfits manuales siguen disponibles si Ollama no está instalado.

En Windows, el instalador ofrece un acceso directo al escritorio. Elige un archivo ICO propio o cancela el selector para usar la percha incluida. El acceso abre la instancia personal en su puerto activo. Puedes volver a ejecutar escritorio.ps1 desde PowerShell para actualizarlo.

En la importación por lotes, asigna el mismo número a las imágenes de una pieza. La primera fila del grupo define su nombre y categoría. Puedes elegir una portada por grupo. En Outfits, selecciona tu espacio para consultar qué piezas están allí. Resumen abre el inventario por espacio y categoría e indica cuántas prendas tienen precio. Ajustes permite seguir la apariencia del sistema o elegir claro u oscuro.
