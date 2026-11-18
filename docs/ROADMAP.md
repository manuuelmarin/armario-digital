# Roadmap

## Estado de auditoría independiente — 18 de noviembre de 2026

La rama `main` consultada está en el commit `78793ddc458ad0e3a917fe5b77c8ead4fab83d4b`, preview 0.3.1, esquema 9. La PR #10 está integrada y el workflow de calidad de ese commit concluyó correctamente. Los resultados históricos no sustituyen una nueva ejecución.

Una auditoría independiente del 1 de noviembre examinó una copia local 0.3.1 sin metadatos Git; no pudo cotejarla con el remoto. Reprodujo los siguientes hallazgos, que **deben verificarse de nuevo en el commit indicado antes de afirmar que afectan a main**:

- [ ] H01: unificar la selección de portada tras reordenar y borrar fotografías; comprobar ficha, catálogo y fuente de visión.
- [ ] H02: conservar ubicación y estilo al sustituir desde un outfit guardado, con valores explícitos para los que carecen de procedencia.
- [ ] H03: comprobar identidad estable de prendas fijadas y excluidas al reintentar una tarea; tratar capturas antiguas sin identidad inequívoca.
- [ ] H04: validar claves externas y restricciones relevantes por esquema al verificar y restaurar copias; probar esquemas 1–9 y restauraciones rechazadas.
- [ ] H05: definir y conservar exclusiones al realizar sustituciones sucesivas.
- [ ] H06: comunicar la ausencia de la foto fuente antes de presentar una prenda como lista o de encolar una tarea.

En una sesión posterior se informó de un parche 0.3.2 y pruebas, pero esa copia temporal se perdió y no se publicó. **No considerar esos cambios integrados ni sus pruebas verificadas en main.** Tras reproducir y corregir, ejecutar regresiones, suite completa, navegador, controles de formato y CI Windows/Linux; revisar además los textos sobre sustituciones y validación de copias. La instalación interactiva en Windows y la calidad, latencia y memoria de los modelos reales en el equipo objetivo siguen pendientes.

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
