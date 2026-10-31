# Documentación de Armario Digital

Aplicación local y monousuario en Python. La versión de la aplicación se declara en `pyproject.toml`; la del esquema, en `armario/db.py`. Son versiones distintas: una mejora de interfaz o documentación no exige una migración de datos.

## Utilizar y mantener

| Necesidad | Guía |
|---|---|
| Crear el primer espacio, añadir prendas y preparar una maleta | [Primeros pasos](GETTING_STARTED.md) |
| Actualizar, verificar una copia o restaurar | [Copias y recuperación](BACKUP_RESTORE.md) |
| Entender el alcance y los flujos | [Producto](PRODUCT.md) |
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
| Revisar recursos y condiciones de distribución | [Terceros](THIRD_PARTY.md) · [Publicación](PUBLISHING.md) |

## Mantener las guías coherentes

- Si cambia un flujo, actualiza la guía de uso y el historial.
- Si cambia un esquema o una copia, actualiza el modelo y la recuperación, y verifica una migración con datos relacionados.
- Si cambia una dependencia externa, documenta cuándo se conecta y qué datos salen del dispositivo.
- Registra comandos, entorno y resultados de cada revisión. Una prueba omitida no cuenta como aprobada y una captura no demuestra por sí sola accesibilidad o integridad.

Los ejemplos y capturas deben usar la demo o datos sintéticos. Nunca incluyas inventarios reales, fotografías personales, claves, copias ni rutas privadas.
