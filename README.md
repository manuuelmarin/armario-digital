# Armario Digital

Tu ropa, en su sitio. Aplicación personal para saber qué tienes en Albacete, Madrid, La Manga y cualquier otra ubicación; guardar outfits y preparar maletas.

**Primera versión: 0.1.0.** Funciona en el navegador de tu propio equipo. Un proceso Python, una base SQLite y fotos locales; sin cuentas, Docker ni servicios externos. No registra qué llevas puesto cada día.

## Empezar en Windows

1. Instala **Python 3.11 o posterior** desde [python.org](https://www.python.org/downloads/windows/), incluido el lanzador `py`. Se recomienda Python 3.12.
2. Descarga este repositorio con **Code → Download ZIP** y extrae la carpeta completa. También puedes clonarlo con Git.
3. Abre `instalar.cmd`. La primera instalación requiere internet para descargar las dependencias.
4. Abre `iniciar.cmd`. Se abrirá [http://127.0.0.1:8765](http://127.0.0.1:8765).
5. Añade tu primera prenda. Para cerrar el servidor, pulsa **Ctrl+C** en su ventana.

No se incluye ropa de ejemplo en tu inventario. Los datos permanecen al cerrar y al actualizar el código.

## Qué puedes hacer

- Añadir, editar, archivar y recuperar prendas, con hasta seis fotografías por prenda.
- Guardar marca, talla, color, temporadas, precio, compra, notas y favoritos.
- Buscar sin distinguir tildes o mayúsculas y combinar filtros por ubicación, categoría, temporada y favoritos.
- Crear y renombrar ubicaciones; mover prendas individualmente o en grupo con historial.
- Guardar outfits con prendas de diferentes armarios y consultar sus ubicaciones actuales.
- Crear viajes, importar outfits sin duplicar prendas y preparar una lista con ropa y otros objetos.
- Distinguir lo que está en origen, en destino o en otra ubicación. Confirmar por separado qué prendas han llegado.
- Descargar copias completas verificables y restaurarlas con la aplicación cerrada.

Archivar conserva las relaciones. La eliminación de una prenda utilizada en un outfit o maleta se bloquea para evitar pérdidas accidentales.

## Datos y recuperación

En Windows, los datos se guardan por defecto en `%LOCALAPPDATA%\ArmarioDigital`, fuera del repositorio. Puedes elegir otra carpeta con `ARMARIO_DATA_DIR` o `run.py --data-dir`. Una carpeta nueva empieza vacía: utiliza una copia para trasladar tu inventario.

Desde **Ajustes → Crear y descargar copia** obtienes un ZIP con base de datos y fotos. Conserva otra copia fuera del equipo. Al arrancar se crea una copia diaria y se realizan copias antes de migraciones. No se borran automáticamente copias antiguas.

Consulta [copias y restauración](docs/BACKUP_RESTORE.md) antes de recuperar datos.

## Desarrollo y comprobaciones

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe run.py --dev
```

El modo de desarrollo recarga Python, plantillas y recursos al guardarlos, sin activar un depurador interactivo. En el uso normal se utiliza Waitress, escuchando exclusivamente en `127.0.0.1:8765`.

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

También funciona en Linux/macOS con `python -m venv .venv`, instalación con `pip` y `python run.py`. La integración continua comprueba Windows y Linux. Las instrucciones detalladas de la prueba visual están en [TESTING.md](docs/TESTING.md).

## Actualizar

1. Crea y descarga una copia, verifica el archivo y cierra la aplicación.
2. Actualiza los archivos de código con `git pull --ff-only` o extrae la nueva versión en otra carpeta.
3. Ejecuta `instalar.cmd` y después `iniciar.cmd`.

Si cambia el esquema, el arranque hace una copia previa y aplica migraciones versionadas. Una versión antigua del código rechaza datos con un esquema más reciente.

## Alcance y documentación

Inspiración, meteorología, colecciones, duplicación de prendas, editor libre de collages y aplicación móvil quedan para iteraciones posteriores. No se muestran botones de funciones pendientes.

- [Producto y alcance](docs/PRODUCT.md)
- [Arquitectura y alternativas](docs/ARCHITECTURE.md)
- [Modelo de datos](docs/DATA_MODEL.md)
- [Decisiones e investigación](docs/DECISIONS.md)
- [Pruebas y limitaciones](docs/TESTING.md)
- [Siguientes pasos](docs/ROADMAP.md)

Código propio. No se ha importado código ni recursos de otros armarios digitales.
