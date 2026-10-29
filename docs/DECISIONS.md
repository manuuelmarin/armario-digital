# Decisiones e investigación — 29 de octubre de 2026

## Base propia y alcance acotado

Se revisaron metadatos, README y `package.json` de [Libre Closet](https://github.com/Lazztech/Libre-Closet). La versión indicada en su paquete es 0.6.0; se confirmó Node 22.x, NestJS, MikroORM, SQLite y dependencias para PWA, cuentas, almacenamiento remoto y eliminación de fondos. Ofrece muchas más funciones de las que vamos a implementar inicialmente. No se ha instalado ni auditado exhaustivamente su código: no se afirma haber medido su rendimiento o validado su instalación en Windows.

La petición de [ubicaciones jerárquicas #125](https://github.com/Lazztech/Libre-Closet/issues/125) seguía abierta al consultar. La pérdida de relaciones de outfits descrita en [#129](https://github.com/Lazztech/Libre-Closet/issues/129) fue corregida por [PR #135](https://github.com/Lazztech/Libre-Closet/pull/135), fusionada el 5 de octubre de 2026, commit `636c1f397a7b61393b1bb23a27fa1f4d980e207c`. Por tanto, no se usa ese fallo histórico como argumento de que la versión actual continúe perdiendo datos. La lección aplicada es probar migraciones con relaciones pobladas, además de comprobar que el servidor arranca.

Se revisó el [README de Wardrobe HQ](https://github.com/wardrobe-hq/wardrobe): etiquetas con categorías, estaciones y parte del cuerpo, composición de outfits y meteorología de OpenWeatherMap con clave. Es útil como referencia de organización; no se importó código, iconos ni recursos.

La URL `OpenWardrobe/app` devolvió 404 en la conexión disponible. No se ha verificado si fue movida, retirada o simplemente no era accesible; no se concluye que el proyecto haya desaparecido. Una investigación exhaustiva de aplicaciones comerciales y forks no aporta suficiente valor para bloquear esta primera implementación.

Se contrastaron las opciones Python con documentación primaria de [NiceGUI](https://nicegui.io/) y [Flask/Waitress](https://flask.palletsprojects.com/en/stable/deploying/waitress/). La comparación y sus incertidumbres constan en ARCHITECTURE.md.

Se elige código propio para controlar las reglas de ubicación, outfits y viaje con un único proceso y sin compilación frontend. Las funciones avanzadas preexistentes en Libre Closet quedan fuera de esta entrega. Es una decisión de alcance y mantenimiento, no una afirmación de superioridad general.

## Persistencia y recuperación

SQLite sin ORM reduce dependencias y hace explícitos los cambios de esquema. Las relaciones se protegen con claves foráneas. Los snapshots usan la API de backup y un manifiesto SHA-256; la restauración es offline y conserva toda la carpeta anterior. Los hashes detectan corrupción, no acreditan la autenticidad de una copia frente a un atacante que la reescriba.

## Fotos y diseño

Fotos protagonistas, formularios con datos opcionales, selección mediante tarjetas y navegación corta. Se usan tipografías del sistema e iconos SVG propios, sin peticiones externas. Las fotos se normalizan y se descartan metadatos. No se añade IA ni eliminación automática del fondo al alta.

## GitHub y coste de trabajo

Se creó el repositorio privado desde GitHub web porque el conector no expone creación de repositorios. La conexión instalada solo enumeraba `manuuelmarin/finances`; el código de este proyecto se prepara y publica por la interfaz web sin tocar permisos de la integración ni modificar ese otro repositorio.

No se utilizaron subagentes. La preferencia futura del propietario para delegación autorizada es Terra 6.1, esfuerzo mínimo y tareas cortas, registrada en AGENTS.md.
