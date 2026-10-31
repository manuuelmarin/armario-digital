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

## Dos modelos locales, aprobación y restricciones verificables

Se integra Ollama como servicio local opcional para ejecutar Qwen3-VL 4B Instruct Q4 (visión) y Qwen3 4B Instruct 2507 Q4 (texto). Visión se ejecuta solo bajo solicitud; sus resultados se revisan y reutilizan. Separar modelos permite evaluar outfits sin reenviar fotografías ni recargar visión para cada combinación. No se añade una librería de ML al runtime Python ni una API comercial.

El tipo de prenda identifica también su capa internamente; no se duplican «identificación» y «función» en la ficha. Siete grupos visuales editables separan observación, desconocidos y estimaciones. La composición exacta, marca y otros datos no observables no se fuerzan desde una imagen.

Python controla identidad, filtros, estructura y vigencia; el modelo de texto evalúa la compatibilidad de una preselección acotada. Esta aproximación limita contexto y coste local, con el coste aceptado de no explorar exhaustivamente el armario. La sorpresa se aplica entre resultados valorados, sin presentar azar como razonamiento. Las valoraciones son ordinales sin calibración estadística.

La cola usa SQLite y un solo hilo del proceso ya existente, no un broker externo. No se mantiene el bloqueo de mutación durante HTTP. La cancelación descarta respuestas; no promete interrumpir instantáneamente otro proceso. Etiquetas/digests e instrucciones se registran para auditar cada generación. [LOCAL_AI.md](LOCAL_AI.md) documenta límites y [el registro del cambio](changes/2026-10-31-local-ai.md) distingue pruebas simuladas de inferencia real.
