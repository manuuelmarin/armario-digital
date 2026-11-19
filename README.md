# Armario Digital

Abre la misma web en Edge o Chrome de Windows. Elige una carpeta del PC para guardar el catálogo SQLite, las fotos y las copias. Desde la web puedes organizar prendas por ubicación, crear outfits y preparar maletas con traslados explícitos.

[Abrir mi armario](https://manuuelmarin.github.io/armario-digital/) · [Ver la demo ficticia](https://manuuelmarin.github.io/armario-digital/#/demo) · [Traer mi armario anterior](docs/WINDOWS_PAGES.md)

## Primer uso

- **Si ya tienes prendas**, abre el programa anterior, crea un ZIP en **Ajustes → Crear y descargar copia** y sigue los pasos de **Traer una copia** en la web.
- **Si empiezas de cero**, pulsa **Crear armario**, elige una carpeta vacía y crea tu primera ubicación en **Ajustes**.
- **Para volver**, abre la misma URL con el mismo perfil. Puedes instalar la web como aplicación desde el navegador.

## Desarrollo

El cliente estático está en [web/](web/). Comparte las migraciones SQL y el formato de copia con la aplicación Python, que se conserva para exportar, recuperar y comprobar datos históricos. La distribución web incluye los flujos manuales. La IA queda aplazada.

[Arquitectura y aceptación](docs/MIGRACION_PAGES.md) · [Uso en Windows](docs/WINDOWS_PAGES.md) · [Documentación histórica y técnica](docs/README.md) · [Historial](CHANGELOG.md)
