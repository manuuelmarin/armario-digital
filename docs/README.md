# Documentación de Armario Digital

[Volver a la portada](../README.md) · [Probar la demo](GETTING_STARTED.md#probar-la-demo) · [Ver el catálogo en pantalla estrecha](assets/mobile.png)

## Utilizar y mantener

| Necesidad | Guía |
|---|---|
| Instalar la aplicación, crear un espacio y preparar una maleta | [Primeros pasos](GETTING_STARTED.md) |
| Actualizar, verificar una copia o restaurar | [Copias y recuperación](BACKUP_RESTORE.md) |
| Entender el alcance y los flujos | [Producto](PRODUCT.md) |
| Preparar modelos locales, revisar descripciones y generar outfits | [Asistencia local](LOCAL_AI.md) |
| Consultar límites y tratamiento de datos | [Seguridad](../SECURITY.md) |
| Saber qué ha cambiado y qué falta | [Historial](../CHANGELOG.md) · [Hoja de ruta](ROADMAP.md) |

## Desarrollar y revisar

| Necesidad | Guía |
|---|---|
| Preparar el entorno y proponer cambios | [Contribución](../CONTRIBUTING.md) · [Reglas del repositorio](../AGENTS.md) |
| Localizar responsabilidades y almacenamiento | [Arquitectura](ARCHITECTURE.md) · [Modelo de datos](DATA_MODEL.md) |
| Entender las elecciones técnicas | [Decisiones](DECISIONS.md) |
| Ejecutar pruebas y distinguir evidencia de cobertura | [Verificación](TESTING.md) |
| Consultar referencias y revisiones anteriores | [Auditoría de producto](AUDIT.md) |
| Consultar los hallazgos y correcciones de la versión 0.3.1 | [Auditoría 0.3.1](audits/2026-10-31-project.md) |
| Revisar el desarrollo de la asistencia local | [Registro del cambio](changes/2026-10-31-local-ai.md) |
| Revisar recursos y condiciones de distribución | [Terceros](THIRD_PARTY.md) · [Publicación](PUBLISHING.md) |

## Mantener las guías coherentes

- Si cambia un flujo, actualiza la guía de uso y el historial.
- Si cambia un esquema o una copia, actualiza el modelo y la recuperación, y verifica una migración con datos relacionados.
- Si cambia una dependencia externa, documenta cuándo se conecta y qué datos salen del dispositivo.
- Registra comandos, entorno y resultados de cada revisión. Una prueba omitida no cuenta como aprobada y una captura no demuestra por sí sola accesibilidad o integridad.

Los ejemplos y capturas deben usar la demo o datos sintéticos. Nunca incluyas inventarios reales, fotografías personales, claves, copias ni rutas privadas.
