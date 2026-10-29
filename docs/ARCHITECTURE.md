# Arquitectura

## Componentes

Un proceso Python sirve HTML y recursos locales, aplica las reglas del dominio y accede a SQLite. No hay una SPA ni una compilación frontend. Waitress es el servidor normal; el modo de desarrollo utiliza recarga de archivos sin depurador interactivo.

| Módulo | Responsabilidad |
|---|---|
| `run.py` | Lanzador, exclusión de instancias, modo demo y recuperación offline |
| `inventory.py`, `looks.py`, `trips.py`, `settings.py` | Rutas y flujos por funcionalidad |
| `domain.py` | Validaciones y operaciones compartidas |
| `queries.py` | Lecturas de prendas con su imagen principal y entidades permitidas |
| `db.py`, `migrations/` | Conexiones, integridad y evolución del esquema |
| `images.py` | Validación, orientación, recodificación y resoluciones |
| `backups.py` | Snapshots, manifiestos, verificación y restauración |
| `demo.py` | Colección ficticia e ilustraciones originales, sin datos reales |
| `templates/`, `static/` | Plantillas, estilos por responsabilidad, fuentes e interacciones progresivas |

## Persistencia y concurrencia

Las conexiones se abren por solicitud y siempre activan claves foráneas. Las escrituras adquieren un bloqueo común dentro del proceso y las operaciones relacionadas utilizan transacciones. El punto de entrada soportado es `run.py`, que además adquiere un bloqueo del sistema operativo para impedir procesos simultáneos sobre la carpeta.

La restauración se hace con el servidor cerrado. Las copias usan la API de backup de SQLite y las imágenes referenciadas por ese snapshot, con mutaciones excluidas durante el empaquetado.

## Interfaz y rendimiento

La galería pagina 48 prendas. La imagen principal se obtiene en la consulta de inventario. La biblioteca de outfits carga sus componentes en conjunto, evitando una consulta por combinación.

Las fotografías usan variantes de 512, 1.024 y hasta 4.096 px y atributos `srcset` y `sizes`. Las fotos anteriores mantienen una ruta de compatibilidad sin regeneración destructiva. Las imágenes y fuentes son locales; no se necesitan CDN. HTML y copias no se cachean; recursos estáticos e imágenes con nombres únicos tienen políticas de caché diferenciadas. En desarrollo se desactiva esa caché.

Los estilos se dividen en `tokens.css` (variables y fuentes), `app.css` (base y estructura), `components.css` (pantallas y componentes) y `responsive.css` (adaptación y accesibilidad). Las plantillas usan formato Jinja verificable con djLint.

JavaScript mejora selección masiva, filtros móviles, búsqueda en selectores, vista previa y galería. Los formularios siguen siendo operativos sin JavaScript. El selector de outfits todavía renderiza el armario activo completo; la paginación del selector queda pendiente para colecciones muy grandes.

## Decisiones

Se comparó reutilizar Libre Closet, usar NiceGUI y separar frontend y API. Se eligió Flask + Jinja + SQLite por el alcance local, la edición directa de HTML/CSS y un único proceso sin compilación frontend. El coste aceptado es implementar y mantener capacidades que otras soluciones ofrecen ya, como el collage libre o una PWA.

No se han medido comparativamente esos frameworks ni se atribuyen garantías de rendimiento a alternativas no ejecutadas. Las referencias de producto están en [AUDIT.md](AUDIT.md).
