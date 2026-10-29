# Arquitectura

Se elige **Flask + Jinja + SQLite + Pillow + Waitress**. El navegador recibe HTML del mismo proceso que gestiona los datos. JavaScript se limita a previsualizar fotos, contar selecciones y confirmar la eliminación de una foto. Los formularios y la persistencia no dependen de una SPA.

| Alternativa | Ventaja para este producto | Coste o incertidumbre | Decisión |
|---|---|---|---|
| Personalizar Libre Closet 0.6.0 | Catálogo, editor de outfits, traducciones, fotos y meteorología existentes | Adaptar ubicaciones y viajes; mantener un fork con Nest, ORM, generación de assets y varias funciones ajenas al uso local | Buen candidato si primasen collage/PWA; no se adopta en este núcleo |
| NiceGUI + SQLite | Una base Python y componentes preparados | Añade su modelo de sesiones y transporte; libertad visual y flujo de formularios pendientes de validar con un prototipo | No se instala ni se atribuye rendimiento no medido |
| React + FastAPI + SQLite | Gran flexibilidad de interacción | Dos cadenas de herramientas, contrato API y estado de cliente para un CRUD monousuario | Se aplaza hasta que exista una necesidad concreta |
| Flask + Jinja + SQLite | Un proceso, sin compilación frontend, HTML/CSS sencillo y SQL explícito | Hay que escribir funciones que Libre Closet ya ofrece; el collage libre y la PWA no vienen incluidos | Elegida; núcleo implementado y probado |

La valoración es un juicio para este alcance, no un benchmark de calidad de los frameworks. El coste de no reutilizar Libre Closet se ha asumido expresamente; no se pretende reproducir ahora todas sus capacidades.

## Módulos

- `inventory.py`, `looks.py`, `trips.py`, `settings.py`: rutas y formularios por funcionalidad.
- `domain.py`: validaciones y operaciones compartidas de traslado y maletas.
- `queries.py`: proyección de prendas y recuperación de entidades.
- `db.py`, `migrations/`: conexiones, integridad y evolución del esquema.
- `images.py`: validación, orientación, conversión y miniaturas.
- `backups.py`: snapshots, manifiestos, verificación y restauración.
- `templates/`, `static/`: interfaz local, sin CDN ni fuentes externas.
- `run.py`: servidor, exclusión de instancias y comandos de recuperación.

## Ejecución y concurrencia

El punto de entrada soportado es `run.py`. Un bloqueo del sistema operativo impide dos servidores o una restauración simultánea en la misma carpeta. Todas las solicitudes POST adquieren un bloqueo común; cada operación SQL relacionada usa una transacción. La copia usa la API de backup de SQLite y copia las fotos referenciadas por ese snapshot mientras se excluyen mutaciones.

Las lecturas usan conexiones por solicitud. Las galerías consultan 48 prendas por página y cargan miniaturas de forma diferida. Los selectores de outfits/maletas muestran el armario activo completo: la búsqueda y paginación del selector quedan como mejora si el inventario crece.

No inicies varios procesos WSGI directamente sobre estos datos: el bloqueo entre mutaciones es interno al proceso y el bloqueo de instancia se aplica en `run.py`. No se soportan carpetas de red ni edición externa simultánea de SQLite o de las fotografías.

## Seguridad local

Loopback obligatorio en el lanzador, hosts permitidos, token CSRF por sesión, comprobación de origen para escrituras, escape HTML, CSP sin código externo y rutas de fotos validadas. No se descargan URLs del usuario. Las fotos se validan por su contenido, se reorientan y recodifican sin EXIF. No se incluye autenticación: el acceso desde otros equipos exige un diseño y una revisión específicos.

Dependencias de ejecución y herramientas fijadas en los archivos `requirements`. La aplicación no necesita internet tras instalarse. Waitress soporta Windows directamente, según la [documentación de Flask](https://flask.palletsprojects.com/en/stable/deploying/waitress/).
