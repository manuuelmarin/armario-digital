# Producto

Armario Digital es un catálogo visual local para organizar prendas, componer outfits y preparar viajes. El diseño prioriza fotografías, consulta rápida y edición progresiva de metadatos.

## Reglas del dominio

- Cada prenda representa un artículo físico y mantiene una identidad estable.
- Una prenda tiene un espacio actual inequívoco. Los espacios se configuran durante el uso.
- Un outfit es una combinación guardada. Puede incluir prendas de diferentes espacios y conservar artículos archivados ya asociados.
- Una maleta es una lista de preparación. Importar un outfit produce una lista independiente de referencias, sin duplicar prendas.
- Preparar una maleta no cambia ubicaciones. Los traslados se confirman de manera explícita y transaccional.
- Archivar conserva las relaciones. Eliminar una prenda en uso se restringe hasta retirar sus referencias.

## Versión 0.2

Incluye inventario con fotografías, metadatos opcionales, temporadas múltiples, favoritos, archivo, búsqueda, filtros y ordenación; espacios editables; biblioteca de outfits; listas de viaje y objetos libres; fotos adaptadas a densidad de pantalla; colecciones y etiquetas sin cambios de ubicación; importación por lotes; tableros con imágenes, notas y enlaces; meteorología opcional; copias verificadas, limpieza manual de copias diarias y restauración offline.

La primera instalación no inserta espacios ni artículos. La demo y las pruebas crean sus propias entidades ficticias en carpetas aisladas.

## Versión 0.3: asistencia local opcional

Conserva los flujos existentes e incorpora descripciones visuales con siete grupos revisables y generación de outfits a partir de perfiles aprobados. Dos modelos locales mediante Ollama separan visión y evaluación textual. Permite recomendación, sorpresa entre candidatos valorados, prendas fijadas, filtros y cambio de una pieza. No cambia ubicaciones ni guarda automáticamente propuestas del modelo. La creación manual continúa disponible sin instalar modelos. Véase [IA local](LOCAL_AI.md).

## Límites

No incorpora cuentas, sincronización remota, funciones sociales, publicación web automática ni registro diario de uso. Incluye tableros de inspiración y collage con posición y anchura ajustables; la exportación del collage sigue pendiente. La meteorología opcional se actualiza manualmente con coordenadas y conserva la última previsión. El modo de distribución actual es local y monousuario.
