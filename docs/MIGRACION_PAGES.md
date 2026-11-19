# Migración de distribución y pruebas de aceptación

Guía de referencia revisada el 19 de noviembre de 2026. Rama `migracion/pages-carpeta-local`. Se consultó `main` en `6b19834925b5826509ef64b155c776ba76b77f14`. Las PR [#11](https://github.com/manuuelmarin/armario-digital/pull/11) y [#13](https://github.com/manuuelmarin/armario-digital/pull/13) seguían abiertas en `6de21286fd56b3901614b2ce88dbf7c94bad99e3` y `a7d0073d6899f3a7577f72f8930abab602d825a4`. Se portaron los contratos manuales desde esas referencias. [PR de migración y checks](https://github.com/manuuelmarin/armario-digital/pull/14)

## Formatos y responsabilidades

El build de Vite empaqueta el cliente, las nueve migraciones SQL originales, las fuentes locales, el trabajador y el WASM de la misma versión de sql.js. El acceso diario a la carpeta elegida pertenece a File System Access. IndexedDB recuerda la referencia a la carpeta. El navegador comprueba el permiso al reconectar. La caché de la PWA contiene únicamente los recursos estáticos enumerados por el build.

| Recurso | Contrato |
|---|---|
| `armario.json` | Formato de carpeta 1, UUID estable. Se publica después de verificar la primera revisión. El bloqueo de inicialización es común a creación y restauración. |
| `catalogo/{a,b}.sqlite` y `{a,b}.commit.json` | Generaciones alternas, revisión, operación, SHA-256 anterior y actual, tamaño y esquema. Se releen los archivos después de cerrar la escritura. |
| `images/` | Original WebP, preview y thumbnail. Cada imagen nueva comparte un token de 32 caracteres. Se conservan los nombres históricos. Los archivos de generaciones anteriores se mantienen para recuperación. |
| ZIP formato 1 | `wardrobe.sqlite`, `manifest.json`, variantes de prendas y de tableros. Esquemas SQLite 1–9 en la entrada y 9 en la salida web. Hash, decodificación, estructura de tablas y acciones de claves externas, integridad SQLite y conjunto exacto de archivos. |
| `backups/` | La copia diaria usa el día UTC. Las copias manuales y anteriores a una migración se conservan durante la limpieza de diarias. |
| Escritura | Un escritor por UUID y perfil, cola por sesión, UUID de intención y revisión de partida. Un reintento reconocido recupera la confirmación. Una intención desconocida con revisión antigua se rechaza. El bloqueo entre pestañas tiene alcance de origen y perfil. |
| Red | Recursos estáticos propios. El usuario activa la previsión o abre un enlace de inspiración de manera explícita. |

## Paridad de operaciones

Cada operación de escritura que figura en la tabla utiliza una revisión confirmada o, para restaurar, una carpeta de destino nueva. Los casos citados están en `web/tests`. Las pruebas de varias operaciones se agrupan por recorrido.

| Origen | Destino y operaciones manuales | Evidencia |
|---|---|---|
| settings, demo | Crear, detectar y abrir, reconectar, desconectar, demo aislada, alta/renombrado/baja de ubicaciones y gestión de categorías | T01, T03, T07 |
| inventory, queries | Catálogo, ficha, búsqueda con normalización de acentos, filtros combinados, orden, paginación, alta, edición, favorito, archivo y baja confirmada. Traslado y actualización de categoría, temporada o etiqueta en lote | T02, T04, T07 |
| images, inventory, #11, #13 | Agrupación de fotos con nombre/categoría/ubicación por grupo, hasta seis por prenda, orden y portada compartidos entre vistas, original a demanda y reparación | T04, T07, T08 |
| looks, domain, #13 | Búsqueda, favoritos, disponibilidad por ubicación, crear, editar, duplicar y eliminar outfits. Un outfit importado se abre y edita como cualquier otro | T05, T07 |
| trips, #13 | Viajes, edición de fechas, selector paginado con selección persistente, añadir outfit, prendas u objeto libre, preparar/quitar, impresión, duplicar, vuelta, traslado confirmado y eliminación | T05, T07 |
| organization | Alta, edición y eliminación de colecciones y etiquetas, asociación de varias prendas, conservación de miembros archivados | T05, T07 |
| boards | Crear, renombrar y eliminar tableros, imágenes, enlaces y edición de la posición y el tamaño del collage | T05, T07, T10 |
| weather | Consulta manual de cinco días, fecha, coordenadas y última respuesta válida, borrado | T10 |
| inventory, templates, static, #13 | Resumen navegable, cobertura de precios, temas, menú móvil, impresión, foco y controles de formulario | T07, T11 |
| backups, db, run | Crear/descargar y verificar copias, importar, restaurar en otra carpeta, copia diaria y anterior al cambio de esquema, limpieza explícita y recuperación de revisiones | T01–T06, T08 |
| Aplicación instalable | Ruta por fragmento, instalación de escritorio, actualización coordinada entre pestañas, segunda versión y trabajo sin conexión | T09, T11, T12 |

Los tres casos históricos de asistencia de #11 quedan aplazados con su implementación Python y sus regresiones en `tests/test_independent_audit.py` de aquella PR. Son el contexto de ubicación/estilo al sustituir, la identidad de las prendas en un reintento y las exclusiones acumuladas entre sustituciones. La web conserva pasivamente las tablas históricas. El trabajador web atiende operaciones SQLite y no ejecuta trabajos de asistencia.

## Registro de etapas

| Etapa | Revisión | Comprobación | Resultado |
|---|---|---|---|
| Base | `6b19834` | Pytest, Ruff y formato, djLint, siete recorridos del legado en Chromium/Linux | 107 pruebas de servidor y siete de navegador aprobadas. |
| Cliente y almacenamiento | `3f1dd1d` | TypeScript y compilación estática | SQLite, carpeta, flujos manuales, contenedores ZIP y PWA implementados. |
| Compatibilidad y actualización | `6b82f58` | 16 pruebas de navegador y una de Node en Linux | Reapertura, rechazo de ZIP inválidos, migración de nueve esquemas, ida y vuelta y cambio de versión offline. |
| Windows | `575248c` | CI sobre el oráculo Python y navegador | Se corrigió el cierre del lector SQLite antes de limpiar el destino temporal en Windows. |
| Integridad y rendimiento | `0cee008` | Guardado con imágenes sintéticas y 30 ediciones por tamaño | Objetivos de rendimiento para 1.000 prendas cumplidos en la máquina de desarrollo. |
| Aceptación final | Último commit y checks de la PR enlazada | Suite de navegador, ensayo nativo en Windows y estado de publicación | El informe de entrega distingue el resultado de cada entorno. |

## Mediciones de almacenamiento

Chromium 153 en Linux 6.18.57 sobre AMD EPYC 9V74. Cada prenda tiene dos fotos sintéticas con tres archivos presentes. Los tiempos en ms miden un directorio OPFS de prueba en esta máquina. El navegador se reinició antes de la primera lectura. La caché del sistema operativo podía seguir caliente. La medición comprende lectura y verificación de los metadatos, consulta y pintado de 24 miniaturas. La creación de copias históricas y el diálogo de Windows se miden aparte del recorrido de almacenamiento. El pico de RSS muestreado suma procesos de Chromium y puede contar memoria compartida varias veces.

| Prendas | Bytes SQLite | Archivos / bytes de imagen | Obtener handle | Abrir metadatos | Galería fría / caliente | Guardar mediana / p95 | Pico RSS MiB |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 401408 | 600 / 37251200 | 10 | 86 | 158 / 84 | 35 / 51 | 562 |
| 1000 | 2158592 | 6000 / 372512000 | 77 | 135 | 201 / 100 | 153 / 198 | 649 |
| 5000 | 9994240 | 30000 / 1862560000 | 321 | 374 | 458 / 367 | 716 / 878 | 927 |

Se conserva SQLite exportado por operación. Para 1.000 prendas la prueba de almacenamiento cumple los objetivos de 2 s de apertura y 500 ms de guardado p95. A 5.000 prendas la confirmación tarda más. Reproducir con `node tests/performance.mjs` desde `web/` tras instalar Chromium. El ensayo completo escribe más de 2 GB en un perfil temporal. El ensayo de 5.000 prendas mide el catálogo. Sus 30.000 archivos de imagen superan el límite de 20.002 entradas del ZIP histórico. Los tiempos corresponden a la máquina Linux descrita.

## Cobertura T01–T12

| Caso | Comprobación reproducible |
|---|---|
| T01 | Crear, cancelar, conservar la sesión, denegar y reconectar. Un fichero testigo sobrevive al intento de crear en carpeta ajena. |
| T02 | Fallos antes y después de publicar imagen, SQLite o confirmación. Se reabre la revisión completa y los reintentos conservan un único traslado. |
| T03 | Inicialización concurrente, dos pestañas, exclusión de escritor, rechazo de una sesión cerrada y una copia diaria por fecha UTC. |
| T04 | Lote atómico con dos grupos, entradas inválidas, máximo de seis, EXIF, transparencia, cambio de portada y reparación del original o la miniatura ausentes. |
| T05 | Nueve ZIP producidos por Python, uno por esquema. Se comparan las tablas después de restaurar y migrar. |
| T06 | Rechazo de ZIP incompatibles, corruptos o con datos relacionales incompletos. |
| T07 | Recorrido por catálogo, colecciones, etiquetas, outfit, maleta, tablero y resumen. Se verifican precios conocidos y listados por ubicación tras el traslado explícito. |
| T08 | JPEG nuevo convertido en tres variantes. Reimportación en Python y en web con cotejo de hashes y relaciones. |
| T09 | Dos compilaciones servidas en la subruta del proyecto. Se conserva un formulario abierto durante la actualización y se guarda otra edición sin conexión. |
| T10 | Captura de tráfico con datos ficticios, incluida la consulta meteorológica explícita y la conservación de la última respuesta tras un fallo. |
| T11 | Foco de teclado, reconexión, ancho de 320 px, menú móvil y conservación de una caché de otra aplicación. |
| T12 | Ensayos en escritorio Windows con dos navegadores instalados, selector nativo, carpeta NTFS, perfil nuevo, permisos, volumen virtual de 64 MiB y acceso directo. Cada resultado se registra por navegador en los checks de la PR. |

## Reproducir la aceptación

Desde la raíz instala `requirements-dev.txt` en un entorno virtual y ejecuta las pruebas indicadas en [TESTING.md](TESTING.md). Desde `web/`:

```sh
npm ci
npm run check
npm run lint
npm test
npm run build
python tests/oracle.py fixtures .fixtures
npx playwright install chromium
npm run test:e2e
```

`PYTHON` y `BROWSER_EXECUTABLE` admiten rutas al intérprete y al Chromium de desarrollo. Los tests del cliente compilado se sirven en `/armario-digital/`. Los ensayos que inyectan fallos utilizan los módulos de origen con SQLite WASM y archivos reales en OPFS. El comparador Python coteja cada fila migrada y las tres variantes de las fotos nuevas. La prueba A → B utiliza dos compilaciones y un perfil persistente.

El ensayo nativo de Windows se ejecuta desde `web/` con `node tests/windows-native.mjs chrome` y `node tests/windows-native.mjs msedge` en un escritorio de pruebas. Crea datos y perfiles desechables. Conviene probar también con la carpeta que usarás a diario y una copia ficticia antes de importar fotografías personales.

## Publicación y recuperación

El workflow `pages.yml` compila y prueba en una PR. Tras integrar en `main`, sube únicamente `web/dist` y despliega con el entorno `github-pages`. La fuente del sitio debe ser **GitHub Actions**. Un despliegue puede necesitar aprobación del entorno o activación del sitio por el propietario. La URL de proyecto es [Armario Digital](https://manuuelmarin.github.io/armario-digital/). Verifica el estado de despliegue antes de trasladar los datos reales.

Para volver a código conocido, revierte el cambio de código mediante una PR, vuelve a compilar y publica la compilación compatible. Para recuperar datos, conserva la carpeta afectada y abre una restauración en otra carpeta vacía. Se pueden utilizar los dos procedimientos por separado. [Pasos de Windows y recuperación](WINDOWS_PAGES.md)

