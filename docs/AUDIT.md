# Auditoría de producto y repositorio — 0.2

La revisión actual, con los hallazgos y correcciones de la asistencia local, está en [Auditoría 0.3.1](audits/2026-10-31-project.md). Este documento conserva el contraste de producto y la evidencia histórica de 0.2.

Fecha: 29 de octubre de 2026. Alcance: código de la preview 0.1, instalación, interfaz, datos de ejemplo, fotografías, documentación, pruebas y preparación de distribución.

## Referencias

Se consultó documentación pública oficial. Este contraste identifica patrones de producto; no es una prueba exhaustiva de cuentas comerciales ni una evaluación del código interno de esos servicios.

| Referencia | Patrón documentado | Aplicación en 0.2 |
|---|---|---|
| [Whering](https://whering.co.uk/how-it-works) | Incorporación visual de prendas, organización y combinaciones guardadas | Fotografías protagonistas, alta progresiva y biblioteca clara |
| [Indyx](https://www.myindyx.com/how-it-works/) | Catálogo, outfits visuales, colecciones y preparación de viajes | Tarjetas consistentes, selectores buscables y relaciones entre colección y maleta |
| [GetWardrobe](https://help.getwardrobe.com/latest/outfits/planning/) | Listas de viaje con prendas y outfits y una checklist específica | Preparación separada del traslado físico y detección de espacios actuales |
| [Libre Closet](https://github.com/Lazztech/Libre-Closet) | Catálogo autoalojado, imágenes y editor de combinaciones | Referencia de alcance y mantenimiento; se conserva una implementación propia más acotada |

No se importaron layouts, fotografías, logos o código de esas aplicaciones. La interpretación de los patrones y las decisiones de alcance son propias de este proyecto.

## Hallazgos y correcciones

| Área | Hallazgo en 0.1 | Corrección |
|---|---|---|
| Datos iniciales | Espacios de un entorno concreto incluidos en SQL y ejemplos | Instalación vacía, primer uso configurable y fixtures explícitos |
| Documentación | Referencias a conversaciones, cuentas y condiciones de desarrollo | README de producto, guías reutilizables y decisiones técnicas neutrales |
| Presentación | Poca evidencia visual de la aplicación y una demo inexistente | Capturas reales, colección ficticia aislada e ilustraciones originales |
| Diseño | Jerarquía tipográfica y componentes poco definidos | Tokens, fuentes locales, navegación y estados compartidos |
| Visibilidad móvil | Los filtros y acciones ocupaban gran parte de la primera pantalla | Filtros desplegables, acciones masivas contextuales y tarjetas adaptables |
| Fotografías | Una miniatura única en galerías y pérdida de detalle al ampliar | Master de hasta 4.096 px, preview, miniatura y selección por densidad |
| Exploración | Pestañas de espacios que perdían filtros y ausencia de ordenación | URLs que conservan filtros, ordenación validada y búsqueda en selectores |
| Datos y consultas | Lecturas repetidas por outfit y referencias inversas sin índices | Carga conjunta de componentes e índices adicionales |
| Compatibilidad | Fotos y copias anteriores sin campos de preview | Campos opcionales y compatibilidad con esquemas 1–3 |
| Distribución | Reglas de instalación mezcladas con decisiones de una instalación | Guías de contribución, seguridad, publicación y límites de la preview |

## Verificación

Se ejecutan pruebas de dominio, integración, migración y recuperación, y recorridos reales de navegador. Se comprueba una primera instalación sin espacios, el alta inicial, la conservación de datos existentes, la selección de imágenes en alta densidad y los controles adaptables. [TESTING.md](TESTING.md) describe comandos, alcance y límites.

La vista actual y la exportación 0.2 no contienen datos de una instalación. La revisión no elimina commits anteriores ni convierte la aplicación local en un servicio multiusuario. La licencia de distribución sigue pendiente de elección.
