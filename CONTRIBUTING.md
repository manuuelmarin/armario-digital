# Contribuir

Las mejoras deben facilitar el uso del armario y mantener sencilla su instalación. Consulta primero las [reglas del repositorio](AGENTS.md) y el [mapa de documentación](docs/README.md).

## Preparar el entorno

Usa Python 3.12 y un entorno virtual. Instala `requirements-dev.txt` y ejecuta `python run.py --dev`. El punto de entrada es el mismo en todas las plataformas; los lanzadores de Windows son accesos auxiliares.

Usa `python run.py --demo` para explorar con datos ficticios y temporales. Para desarrollar con persistencia, elige una carpeta de pruebas independiente mediante `--data-dir`; no utilices tu inventario real.

## Preparar una propuesta

Crea una rama desde `main` con un cambio acotado. Explica el problema, el comportamiento resultante, las comprobaciones realizadas y las implicaciones para datos o compatibilidad. Adjunta capturas de la demo si cambia la interfaz. Usa mensajes de commit descriptivos, por ejemplo `docs: aclarar recuperación` o `fix: conservar asociaciones al editar`.

Las actualizaciones deben preservar inventarios y copias compatibles. Los cambios de esquema requieren migración versionada, copia recuperable y prueba con relaciones pobladas. Actualiza las guías afectadas y el [historial](CHANGELOG.md). No modifiques recuentos históricos para hacerlos pasar por resultados nuevos.

## Verificar

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m djlint armario/templates --check
```

Para navegador, instala Chromium con `python -m playwright install chromium` y activa `RUN_BROWSER_TESTS=1`. La [guía de pruebas](docs/TESTING.md) recoge comandos por plataforma y límites de la evidencia. Revisa el resultado de CI del commit final antes de integrar.

En un cambio exclusivamente documental, comprueba enlaces relativos, rutas, comandos, coherencia con el código y renderizado Markdown. No atribuyas una nueva validación funcional a una simple revisión de texto.

## Datos y distribución

No incluyas fotografías reales, bases, claves, copias, datos de cuentas, rutas privadas ni transcripciones en ejemplos, issues o capturas. Conserva las licencias de fuentes y otros recursos.

La licencia de distribución pública está pendiente. Mantén el acceso actual del repositorio y el alcance local y monousuario. Publicar código, alojar un servicio y sincronizar datos son decisiones diferentes; consulta [publicación](docs/PUBLISHING.md).
