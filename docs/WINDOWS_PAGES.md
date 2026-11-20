# Mi armario en Windows

## Traer el inventario que ya tienes

1. **Abre la aplicación anterior** con el acceso directo que usas habitualmente. Comprueba que ves tus prendas. En **Ajustes → Crear y descargar copia**, guarda el ZIP fuera de la carpeta de destino. Conserva tanto ese archivo como la instalación original. La ubicación predeterminada del legado es `%LOCALAPPDATA%\ArmarioDigital`, aunque puedes haber elegido otra.
2. **Abre Armario Digital en Edge o Chrome de escritorio** con el perfil que usarás habitualmente. En la primera visita necesitas conexión. [Abrir la aplicación](https://manuuelmarin.github.io/armario-digital/)
3. **Pulsa «Traer una copia»**, selecciona el ZIP sin descomprimir y pulsa **Verificar copia**. Comprueba los recuentos de prendas y outfits. La cifra de archivos de imagen incluye originales, miniaturas y vistas previas.
4. **Pulsa «Restaurar en una carpeta vacía»**. Crea, por ejemplo, una carpeta `Mi Armario` en un disco local de tu PC, fuera de OneDrive si Documentos está sincronizado. Selecciónala, concede permiso de escritura y confirma su nombre. En **Armario listo**, comprueba el nombre de la carpeta y los recuentos restaurados. Pulsa **Abrir armario** para ver el catálogo. La aplicación crea su propia estructura. La carpeta del programa Python y la de sus datos deben conservarse por separado.
5. **Comprueba tu armario antes de cambiar de acceso directo**. Abre una prenda conocida y sus fotos, revisa su portada y ubicación y consulta un outfit y una maleta. Cierra y vuelve al mismo enlace. En la barra de direcciones pulsa el icono de instalación si aparece. También puedes usar la opción de instalar la página como aplicación del menú del navegador. Crea o fija el acceso con un nombre reconocible, por ejemplo «Mi armario web». En Edge también puedes escribir `edge://apps`, abrir **Detalles** en la tarjeta **Mi Armario Digital** y elegir **Crear acceso directo en el escritorio**. El icono anterior seguirá abriendo Python.

Si la web indica que la copia es inválida, conserva el mensaje y el ZIP original. Comprueba la copia en la aplicación histórica o crea otra desde allí. Si se interrumpió una restauración, elige otra carpeta vacía para el siguiente intento.

## Volver cada día

Abre el mismo icono. Si aparece **Reconectar**, pulsa y acepta el permiso solicitado. Si cambias de perfil, de navegador o mueves la carpeta con todas las ventanas cerradas, pulsa **Abrir mi carpeta** y selecciona la carpeta que contiene `armario.json`. Utiliza un único navegador y perfil para editar ese armario. Otra pestaña del mismo perfil puede consultarlo en modo de solo lectura.

En un armario nuevo crea una ubicación en **Ajustes** y después añade una prenda. En **Añadir prenda** puedes seleccionar varias fotos y escribir el número de la que quieres como portada. En la ficha puedes volver a elegirla. Para introducir varias prendas utiliza **Importar grupos de fotos**, un grupo por prenda. Un movimiento de prendas en el Explorador de Windows no las registra en el catálogo.

En **Maletas**, marca los artículos preparados. Cuando los hayas llevado, selecciona las prendas que han llegado en **Trasladar a destino** y confirma. La ficha conserva el historial. En **Resumen**, la relación «con precio / prendas» explica cuánto del valor del grupo se conoce. Un precio sin completar se conserva como desconocido.

## Copias, problemas de guardado y actualizaciones

- **Otra copia fuera del disco.** En Ajustes pulsa **Crear y descargar copia**. Cada ZIP incluye el catálogo y sus imágenes verificadas. En un catálogo con muchas fotos, el primer guardado puede esperar mientras se prepara o verifica la copia diaria. Mantén la ventana abierta hasta que aparezca **Guardado**. Guarda algún ZIP en otro soporte. La carpeta conserva las copias manuales, las diarias y, al importar formatos antiguos, la copia anterior a la migración. Ajustes permite verificar una copia y limpiar explícitamente las diarias más antiguas.
- **Una operación se interrumpe.** Conserva la carpeta completa. Reabre el armario para que compruebe ambas generaciones. Si indica recuperación, revisa el último cambio antes de repetirlo. Si ambas generaciones están dañadas, o la aplicación detecta un conflicto o un formato posterior, restaura un ZIP en otra carpeta. Mantén la carpeta original para poder comparar.
- **La copia diaria impide guardar.** Si aparece el nombre de un ZIP dañado, muévelo desde `backups` a otra carpeta para conservarlo y reintenta. Una copia diaria de cero bytes se vuelve a crear automáticamente.
- **La revisión ha cambiado.** Comprueba los datos recién cargados, vuelve a introducir el cambio que necesites y guarda. Usa siempre el mismo perfil de Chrome o Edge para editar esa carpeta.
- **Falta una foto.** Abre la ficha y utiliza **Reparar o sustituir** con el archivo correspondiente. Si falta el permiso, reconecta. Si falta espacio, libéralo fuera de la carpeta del armario o restaura la última copia en un disco con espacio. Espera a **Guardado** antes de cerrar la ventana.
- **Programa actualizado.** En la misma URL aparece **Nueva versión disponible · Actualizar**. Guarda los formularios pendientes o descártalos explícitamente al salir de ellos. El sitio puede trabajar sin conexión después de que el navegador haya terminado de descargar la versión completa. La primera visita desde un perfil nuevo necesita conexión.
- **Volver a una versión anterior.** El administrador puede volver a publicar una compilación anterior compatible desde GitHub. Para volver a datos anteriores, restaura el ZIP elegido en una carpeta nueva y comprueba qué ediciones contiene. Conserva las ediciones posteriores en la carpeta actual.
- **Privacidad.** GitHub sirve el programa y las ilustraciones de demostración. El catálogo, las fotos y los ZIP se procesan en el PC. Una petición explícita en **Tiempo** envía coordenadas a Open-Meteo. Un enlace de inspiración se abre cuando lo pulsas. Las rutas de proyectos en el mismo dominio de Pages comparten origen. Un dominio dedicado permite separar orígenes y exige volver a conceder acceso a la carpeta.

