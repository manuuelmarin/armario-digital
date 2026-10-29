# Trabajo en este repositorio

- Producto personal, local y monousuario. Interfaz en español. Prioriza facilidad de uso y mantenimiento.
- Lee README y los documentos afectados antes de modificar la arquitectura. No añadas cloud, autenticación, Docker o una SPA por inercia.
- No implantes un seguimiento diario de outfits ni estadísticas que dependan de él.
- Datos, fotos, claves, ZIPs y entornos virtuales quedan fuera de Git. Usa datos sintéticos en pruebas.
- Mantén la separación entre vistas, dominio, SQLite, imágenes y copias. No reconstruyas tablas pobladas sin migración segura y prueba con relaciones existentes.
- Añadir prendas a una maleta nunca cambia su ubicación. Todo traslado debe ser explícito y transaccional.
- Antes de entregar: ejecuta las pruebas relevantes, `python -m ruff check .` y `python -m ruff format --check .`. Para cambios de interfaz, revisa escritorio y móvil y ejecuta la prueba de navegador cuando sea posible.
- No declares probado Windows ni un navegador si solo has ejecutado pruebas de servidor en Linux. Registra las limitaciones reales.
- No publiques una versión estable hasta validar instalación y recuperación en el Windows del propietario.
- El propietario prioriza el consumo de tokens: evita subagentes por defecto. Si los utiliza con autorización, elige `gpt-6.1-terra`, esfuerzo `low` (mínimo disponible), contexto breve, una tarea concreta y salida corta; sin delegación recursiva. Si ese modelo no está disponible, trabaja sin subagentes.
- No modifiques otros repositorios del propietario. No expongas el servidor a la red ni subas datos personales.
