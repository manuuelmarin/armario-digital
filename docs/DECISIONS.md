# Decisiones técnicas

## Un proceso local

Flask, Jinja, SQLite, Pillow y Waitress mantienen un único punto de arranque y evitan contratos de API y estado de cliente innecesarios para esta fase. Los módulos siguen las funcionalidades y servicios que requieren responsabilidades diferentes, sin un framework de repositorios o microservicios.

## Configuración y datos separados

Los espacios se crean en el primer uso. Ninguna ubicación, prenda o preferencia de una instalación forma parte del código distribuido. Demo y pruebas tienen fixtures explícitos en almacenamiento aislado.

La eliminación de datos precargados de la migración inicial solo afecta a instalaciones nuevas. No se renombra ni elimina el contenido de una base existente para hacerla coincidir con ejemplos genéricos.

## Imágenes adaptativas

Se usan tres resoluciones locales para mejorar definición y limitar transferencia. No se aplica aumento artificial de resolución. Los campos nuevos son opcionales para preservar compatibilidad con fotografías y copias anteriores. Las fuentes se incluyen con sus licencias; no se cargan desde servicios externos.

## Integridad antes que eliminación automática

Las referencias a prendas y espacios se restringen cuando su borrado destruiría relaciones de uso. El archivo proporciona una alternativa reversible. La recuperación valida completamente una copia antes de sustituir la carpeta activa y conserva el estado anterior.

## Distribución

La preview se ejecuta en loopback y es monousuario. Publicar el código no implica exponer automáticamente el servicio. Autenticación, sincronización, empaquetado de escritorio y licencia de distribución requieren decisiones específicas antes de ofrecer esas capacidades.

## Mantener Python como base

Se mantiene la lógica en Python y la interfaz en Jinja, HTML, CSS y JavaScript progresivo. No existe una medición que justifique una reescritura en Rust o C. SQLite y Pillow ya utilizan componentes nativos. Antes de extraer una tarea intensiva a otro lenguaje, hay que medirla, revisar consultas y operaciones repetidas, y evaluar el coste de empaquetado en las plataformas soportadas. Esta decisión no impide revisar un componente concreto si aparecen datos que lo justifiquen.
