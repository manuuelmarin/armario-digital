# Roadmap

## Auditoría independiente de noviembre de 2026

La revisión 0.3.2 corrige los seis casos reproducidos sobre 0.3.1 (commit `78793dd`). Las regresiones de portada, ubicación y estilo, identidad en reintentos, claves externas, exclusiones y disponibilidad de fotos están en [las pruebas de auditoría](../tests/test_independent_audit.py). La recuperación con fotos y relaciones se comprueba en los nueve esquemas admitidos.

Siguen pendientes la instalación interactiva en Windows y las mediciones con los dos modelos reales en el equipo de destino.

## 0.2 — Base visual y reutilizable

- Instalación vacía y configuración de espacios.
- Sistema visual consistente, recursos locales y fotografías adaptativas.
- Demo ficticia aislada y documentación de producto.
- Flujos existentes preservados y pruebas de migración/recuperación ampliadas.

## Próximas iteraciones

1. Validar calidad, consumo y latencia de los dos modelos locales con un armario pequeño; la integración opcional y sus controles ya están implementados.
2. Mejorar la búsqueda de localidades para la meteorología y añadir exportación de collages.
3. Ampliar el recordatorio de copias y estudiar una política automática sin riesgo de borrar la única copia válida.

La paginación visual de selectores y la ordenación de fotografías están implementadas. Duplicación controlada de prendas, más capas/accesorios y preselección de outfits para armarios muy grandes quedan sujetos a validación de uso, sin sustituir la edición manual.

## Según validación de uso

Temporadas de outfits, espacios jerárquicos, plantillas de viaje, importación/exportación legible y modo oscuro. El empaquetado de escritorio y la sincronización requieren evaluar instalación, seguridad y recuperación en su plataforma.

## Distribución pública

Seleccionar la licencia, revisar el historial y los recursos, y probar instalación/actualización/restauración con los paquetes que se distribuyan. El servicio multiusuario queda fuera de la preview local. [PUBLISHING.md](PUBLISHING.md) describe esos límites.
