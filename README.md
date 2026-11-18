# Armario Digital

Un armario visual para saber qué tienes, dónde está y qué llevarte de viaje. Se abre en el navegador y guarda el inventario y las fotos en tu ordenador.

[Probar la demo](docs/GETTING_STARTED.md#probar-la-demo) · [Instalar](docs/GETTING_STARTED.md#instalar-y-abrir) · [Documentación](docs/README.md)

![Inventario de la demo con prendas ilustradas y filtros por ubicación, categoría y temporada](docs/assets/desktop.png)

- **Armarios por ubicación.** Encuentra una prenda por su foto y consulta en qué armario la dejaste.
- **Outfits.** Guarda combinaciones propias o pide sugerencias a la [IA local opcional](docs/LOCAL_AI.md).
- **Maletas.** Añade prendas o un outfit entero, marca lo que ya has preparado y confirma el traslado cuando llegues.

## Empezar

En **Windows**, con Python 3.11 o posterior, [descarga el proyecto](https://github.com/manuuelmarin/armario-digital/archive/refs/heads/main.zip), extrae el ZIP y ejecuta `instalar.cmd` una vez. Después, abre `iniciar.cmd`.

¿Prefieres verlo con ropa de ejemplo? Tras instalarlo, ejecuta `.\iniciar.cmd --demo` desde PowerShell en la carpeta del proyecto. La demo usa un inventario temporal. [Instrucciones para Linux y macOS](docs/GETTING_STARTED.md#linux-y-macos)

## Mapa del repositorio

| Ruta | Qué encontrarás |
| --- | --- |
| [`run.py`](run.py) | Arranque, demo y recuperación de copias |
| [`armario/`](armario/) | Lógica del catálogo, outfits y maletas |
| [`armario/templates/`](armario/templates/) · [`armario/static/`](armario/static/) | Pantallas, estilos y recursos visuales |
| [`armario/migrations/`](armario/migrations/) | Evolución de la base de datos SQLite |
| [`tests/`](tests/) · [`.github/workflows/`](.github/workflows/) | Pruebas y comprobaciones en Windows y Linux |
| [`docs/`](docs/README.md) | Guías de uso, datos y arquitectura |

[Guía de desarrollo](CONTRIBUTING.md) · [Historial de cambios](CHANGELOG.md)
