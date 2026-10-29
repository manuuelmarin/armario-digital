# Preparar una publicación

## Estado actual

La versión 0.2 tiene configuración genérica, una demo aislada, ejemplos ficticios, fuentes con licencias incluidas, documentación de contribución y comprobaciones automatizadas. No incluye inventarios, fotografías reales ni credenciales en los archivos de distribución.

## Código e historial

El contenido actual está separado de los datos de cada instalación. El historial anterior a 0.2 conserva ejemplos específicos del entorno de desarrollo. Hacer público un repositorio existente también permite consultar esos commits: hay que revisar el historial completo antes de cambiar la visibilidad.

El ZIP de código de 0.2 no contiene `.git` y permite revisar una exportación sin ese historial. Una publicación desde una exportación limpia y una publicación del repositorio histórico son decisiones distintas. La auditoría no reescribe ni fuerza el historial existente.

## Licencia y recursos

Debe elegirse una licencia de distribución antes de anunciar el código como reutilizable. No se presupone una licencia abierta. Las fuentes DM Sans y DM Serif Display se distribuyen bajo SIL Open Font License 1.1; los avisos están en `armario/static/fonts/`. Los iconos e ilustraciones de demo son originales del proyecto.

Las capturas de presentación deben generarse desde `--demo`. No deben utilizarse bases reales ni fotografías de una instalación como ejemplos distribuidos.

## Paquetes

Para cada plataforma que se anuncie, comprobar desde una carpeta nueva: instalación, arranque, cierre, actualización de datos poblados, creación de copia y restauración en una carpeta alternativa. La CI valida el código en Windows y Linux; no sustituye toda la experiencia gráfica de instalación. macOS requiere validación específica antes de anunciar un paquete estable.

## Servicio accesible por internet

La preview escucha exclusivamente en `127.0.0.1` y no implementa cuentas. Una versión alojada necesita un diseño específico de autenticación, autorización, cifrado, almacenamiento y copias. No se ha configurado GitHub Pages ni se realiza despliegue automático.
