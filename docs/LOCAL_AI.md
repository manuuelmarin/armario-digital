# Asistencia local: descripciones y outfits

La asistencia es opcional y está desactivada en una instalación nueva. El catálogo y los outfits manuales funcionan sin Ollama. Se mantienen Python, Flask, Jinja y SQLite; no se añade PyTorch ni una dependencia de pago.

La revisión 0.3.1 corrige sustituciones de capas, contraste de transparencias y comprobaciones de integridad/procedencia. El [informe de auditoría](audits/2026-10-31-project.md) recoge la evidencia. Las propuestas de outfits del formato anterior necesitan regeneración explícita; se conservan las descripciones y combinaciones ya guardadas.

## Qué hace cada modelo

| Trabajo | Modelo local admitido | Entrada | Resultado |
|---|---|---|---|
| Describir una prenda | `qwen3-vl:4b-instruct-q4_K_M` | Una versión temporal de la fotografía principal, hasta 1.024 px | Narrativa y siete grupos estructurados, pendientes de revisión |
| Proponer combinaciones | `qwen3:4b-instruct-2507-q4_K_M` | Descripciones aprobadas resumidas, candidatos reales y preferencias | Valoraciones y explicaciones de combinaciones completas |

Ollama ejecuta los modelos; no es otro modelo. Las etiquetas indicadas publican pesos con licencia Apache 2.0. Sus descargas anunciadas son aproximadamente 3,3 y 2,5 GB, respectivamente; esos tamaños **no equivalen al consumo de RAM**. Se descargan aparte y no se incluyen en el repositorio ni en las copias del armario. Su uso local no tiene una tarifa por llamada a una API comercial.

Son modelos generales. No se presentan como un recomendador especializado entrenado con tu armario ni como una medida objetiva de buen gusto.

## Preparación en Windows

1. Instala una versión reciente de [Ollama](https://ollama.com/download) compatible con Qwen3-VL. Su ficha indica como mínimo Ollama 0.12.7; es preferible una versión mantenida compatible.
2. En las variables de entorno de tu usuario de Windows, añade estos valores para **Ollama**, cierra Ollama desde su icono y vuelve a abrirlo:

   | Variable | Valor | Propósito |
   |---|---|---|
   | `OLLAMA_HOST` | `127.0.0.1:11434` | Mantener el servicio en el propio equipo |
   | `OLLAMA_NO_CLOUD` | `1` | Desactivar funciones cloud de Ollama |
   | `OLLAMA_NUM_PARALLEL` | `1` | Una inferencia por modelo a la vez |
   | `OLLAMA_MAX_LOADED_MODELS` | `1` | Un modelo cargado a la vez |

   Estas variables pertenecen al proceso de Ollama. Ponerlas solo en la terminal de Armario Digital no reconfigura un Ollama ya abierto. No amplíes su dirección a `0.0.0.0`.

3. Abre una terminal y ejecuta:

   ```powershell
   ollama pull qwen3-vl:4b-instruct-q4_K_M
   ollama pull qwen3:4b-instruct-2507-q4_K_M
   ollama list
   ```

4. Arranca la app con `iniciar.cmd`. Abre **Ajustes → Configurar asistencia local → Comprobar Ollama y modelos**. La comprobación consulta la instalación; no descarga pesos ni analiza fotos.
5. Activa la asistencia y guarda las preferencias. Solicita las tareas desde sus botones.

En Linux/macOS usa la misma configuración en el entorno del servicio o aplicación de Ollama. Consulta la [configuración oficial por plataforma](https://docs.ollama.com/faq).

### Un ordenador con 32 GB de RAM

Los modelos 4B cuantizados y la ejecución secuencial son una elección inicial razonable, no una garantía de velocidad. La CPU, GPU, memoria de vídeo, contexto y otros programas afectan al consumo y la latencia. No se ha medido el equipo objetivo ni se han ejecutado estos pesos en esta revisión.

La app solicita contexto de 8.192 tokens, hasta 2.200 tokens de salida, una tarea por trabajador y descarga de memoria al finalizar (`keep_alive=0`). Esta decisión reduce la convivencia de modelos, pero cargar cada uno de nuevo puede aumentar el tiempo. Otras aplicaciones que usen Ollama también consumen sus recursos. Consulta `ollama ps` y el Administrador de tareas durante la primera prueba.

## Describir y revisar

Desde una prenda, abre **Revisar descripción → Solicitar análisis visual**. Desde tareas puedes seleccionar hasta veinte prendas con foto para ponerlas en cola. La fotografía principal es la fuente del análisis; las secundarias no se combinan en esta versión.

| Grupo | Qué se revisa |
|---|---|
| Tipo y subtipo | Identificación concreta; la capa que ocupa en el outfit se deriva internamente del tipo |
| Paleta | Color dominante, secundarios, proporción y contraste |
| Estampado | Tipo, tamaño y distribución |
| Forma y proporciones | Silueta, ancho, mangas y largo de pantalón visible |
| Textura y acabado | Superficie observable, sin inventar composición |
| Construcción y detalles | Cuello, cierre, bolsillos, capucha y otros detalles |
| Estética y formalidad estimada | Hasta cinco estilos; escala ordinal editable de 1 a 5 o «sin estimar» |

Deja vacío lo que no sea observable. Marca, talla, precio y composición exacta siguen en la ficha manual. No se deduce protección térmica ni temporada de una fotografía. La ocasión se elige al generar.

Al terminar, pulsa **Revisar los siete grupos**, corrige y **Guardar descripción revisada**. Una propuesta no modifica por sí sola el inventario ni una descripción aprobada. También puedes rellenar los grupos a mano sin modelos. No hay una segunda ficha de «función en el outfit» que duplique la identificación.

Cambiar o quitar la foto principal deja caducada la revisión anterior hasta que la confirmes para la foto actual. Si cambias la foto, archivas/eliminas la prenda o corriges su descripción durante una inferencia, su resultado se descarta. Dos pestañas no pueden sobrescribir silenciosamente una revisión más reciente.

También se comprueban los bytes reales al ejecutar/publicar resultados y al aprobar o guardar: una foto borrada o modificada fuera de la app no se considera vigente solo por conservar el mismo nombre. Reimporta la fotografía si no coincide con su huella. Las transparencias se componen sobre fondo claro para el JPEG temporal de visión; no se altera la foto guardada.

## Generar outfits

Abre **Outfits → Generar outfits**. Se usan prendas activas con descripción revisada vigente y tipo reconocido.

- **Recomendar combinaciones:** ordena propuestas por la valoración del modelo y muestra hasta tres.
- **Sorpréndeme:** elige al azar entre las propuestas que el modelo ha valorado como coherentes en esa ejecución. No mezcla todo el armario al azar.
- **Completar una prenda:** desde su ficha, pulsa **Completar con esta prenda**, o selecciónala en el generador. Las prendas fijadas deben permanecer en todos los candidatos.
- **Cambiar una pieza:** desde una propuesta, pulsa **Cambiar esta prenda**. Se excluye esa pieza y se fijan las demás; se hace una nueva evaluación. Un outfit guardado ofrece **Buscar alternativa manteniendo el resto**.

Los filtros obligatorios son ubicación, chaqueta/abrigo sí o no, pantalón corto/largo confirmado, permiso de accesorios y prendas fijadas. La ocasión y el estilo son preferencias para el modelo, no garantías verificables por un filtro. Si eliges pantalón corto/largo, no se sustituye por falda o vestido ni por un largo desconocido.

Un candidato completo tiene superior + inferior + calzado, o vestido/mono + calzado. Puede incluir una chaqueta/abrigo y un accesorio. Esta versión admite como máximo una prenda por capa; no modela todavía camiseta + camisa + jersey ni varios accesorios simultáneos. La chaqueta obligatoria puede ser chaqueta o abrigo: el control lo anuncia así.

Sustituir una pieza conserva su capa y el resto: una chaqueta no desaparece por ser opcional, un accesorio necesita otro accesorio y un vestido/mono no se convierte silenciosamente en dos prendas. Si no hay una alternativa revisada con esos filtros, se informa sin generar otro tipo de conjunto. Al partir de un outfit guardado se mantienen los controles de chaqueta y accesorios.

### Cómo se decide

1. Python excluye prendas que no cumplen los filtros y deriva las capas a partir del tipo revisado.
2. Preselecciona hasta cinco prendas por capa, conservando las fijadas. Favorece coincidencia del estilo indicado y cercanía de formalidad; combina y diversifica hasta diez candidatos completos. No calcula todas las combinaciones de un armario grande.
3. Envía al modelo de texto solo los candidatos y sus prendas, con resúmenes de los siete grupos y la narrativa. El presupuesto se acota a 12.000 caracteres de datos retirando candidatos; no vuelve a ejecutar visión. Los textos largos se resumen por truncamiento explícito de campos, no con otro modelo.
4. Qwen valora hasta seis candidatos con armonía, coherencia de estilo/ocasión y equilibrio, cada una de 1 a 5, y explica sus motivos.
5. Python valida de nuevo identidad, estructura, filtros y vigencia. La media ponderada es `(2 × armonía + 2 × estilo + equilibrio) / 5`; se muestran solo propuestas con al menos 3. No son porcentajes ni probabilidades calibradas.
6. Solo **Guardar propuesta** crea un outfit. Antes de guardarlo se vuelven a comprobar las prendas y sus revisiones. No se cambia ninguna ubicación.

La preselección es una aproximación: puede dejar fuera la mejor combinación de un armario grande. La valoración final corresponde al modelo y puede equivocarse. Si no hay candidatos o el modelo no considera coherente ninguno, la app explica el problema; no finge una recomendación ni activa un servicio cloud. La temperatura cero reduce variación, pero no garantiza reproducibilidad exacta entre versiones o equipos.

## Cola, errores y control

La cola y sus resultados se guardan en SQLite. Cada tarea tiene estado, versiones de instrucciones y modelo, huella del modelo instalado y datos de origen. Hay hasta 200 pendientes y se muestran las 100 más recientes. El trabajador se inicia desde `run.py`; `create_app()` por sí solo no inicia hilos ni solicitudes.

- **Pausar:** conserva las pendientes y detiene la siguiente inferencia; la activa puede terminar. La comprobación explícita de instalación sigue disponible.
- **Cancelar:** impide aplicar el resultado. Cerrar una conexión de la app no garantiza detener una inferencia ya iniciada en Ollama.
- **Reintentar:** crea una tarea nueva con el armario actual; nunca se reintenta en bucle automáticamente.
- **Desactivar:** cancela análisis y generaciones pendientes/en curso; conserva descripciones aprobadas y outfits.
- **Cerrar y abrir:** las pendientes siguen su estado; una tarea interrumpida en curso pasa a error y exige reintento explícito. La pausa se conserva.
- **Espera agotada:** el cliente espera hasta 300 segundos de inactividad de socket. La cola se pausa para evitar acumular solicitudes si Ollama sigue trabajando. Comprueba `ollama ps` antes de reanudar. No es un límite estricto del tiempo total de una respuesta que siga enviando datos.

No se mantiene el bloqueo de escritura ni una transacción SQLite durante las llamadas. Puedes seguir editando, preparando maletas y creando copias. La respuesta se aplica en una transacción corta y únicamente si su origen continúa vigente.

## Datos, seguridad y recuperación

El destino del adaptador está fijado a `127.0.0.1:11434`; no admite URL de usuario, proxy de entorno, redirecciones, descarga automática ni fallback cloud. Solo usa `/api/tags` y `/api/chat`. Al modelo de texto no se adjuntan imágenes ni los campos originales de marca, precio, talla, notas y nombres de ubicaciones. Los textos libres de los perfiles aprobados sí se envían al servicio local tal como se hayan revisado, incluido cualquier dato escrito en ellos. Las instrucciones no habilitan herramientas ni ejecución de código.

Los resultados se validan con esquema estricto, opciones cerradas, límites de texto/listas/respuesta y rechazo de claves JSON duplicadas. Los textos se renderizan escapados. Las descripciones y preferencias se tratan como datos no confiables; un modelo puede seguir interpretándolas mal, pero no puede inventar IDs guardables, mover prendas ni ejecutar acciones de la aplicación.

La app verifica la huella de la foto antes de enviarla a visión. Los resultados aprobados, tareas y origen de outfits se incluyen en las copias SQLite. Los pesos y la configuración de Ollama se preparan aparte al restaurar otro equipo. Tras restaurar, las tareas en cola pueden continuar si la asistencia estaba activa; conserva la pausa o desactiva antes de reanudar si no quieres ejecutarlas.

El almacenamiento y las copias no están cifrados por la aplicación. Protege la cuenta y disco del equipo. Ollama local es otro servicio accesible a procesos del propio equipo; su instalación y sus registros se gestionan aparte. El código de Armario no registra imágenes, prompts ni respuestas en sus logs.

En **Tareas → Eliminar historial finalizado** puedes eliminar propuestas y resultados antiguos confirmándolo. Las descripciones aprobadas y el origen de outfits guardados se conservan. Borrar el historial activo no borra copias anteriores. Una edición manual de un outfit retira sus valoraciones originales para no atribuirlas a una combinación modificada.

## Primera validación con modelos reales

Con una pequeña colección ficticia o de prendas cuya descripción puedas verificar:

1. Analiza entre cinco y diez fotos claras de una sola prenda. Comprueba los siete grupos y registra errores y tiempos, sin incorporar esas fotos al repositorio.
2. Revisa las descripciones; genera con y sin chaqueta, corto/largo y una prenda fijada. Comprueba explicaciones y calidad de combinación.
3. Cambia una pieza; verifica que las demás permanecen. Apaga Ollama y comprueba que el armario y la creación manual continúan funcionando.
4. Observa memoria y tiempos con `ollama ps` y las herramientas del sistema. Si la respuesta agota la espera, revisa rendimiento antes de reanudar la cola.
5. Crea, verifica y restaura una copia en otra carpeta. Revisa descripciones, fotos y outfits recuperados.

Las pruebas automáticas de esta integración usan dobles de HTTP/modelo; prueban contratos y fallos, **no calidad de las inferencias reales**. Consulta [TESTING.md](TESTING.md) y el [registro del cambio](changes/2026-10-31-local-ai.md).

## Referencias primarias

Consultadas el 31 de octubre de 2026:

- [Modelo de visión, tamaño y licencia](https://ollama.com/library/qwen3-vl:4b-instruct-q4_K_M).
- [Modelo de texto, tamaño y licencia](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M).
- [Contrato de `/api/chat`](https://docs.ollama.com/api/chat) y [modelos instalados](https://docs.ollama.com/api/tags).
- [Configuración, memoria y ejecución local de Ollama](https://docs.ollama.com/faq).

Al buscar una alternativa desde una combinación guardada, el formulario recupera ubicación y estilo si hay preferencias registradas. Las sustituciones sucesivas de una propuesta acumulan las prendas descartadas. Para reconsiderarlas, inicia una generación nueva. Si una tarea antigua no permite identificar las prendas fijadas o excluidas, vuelve a seleccionarlas en el generador. Una foto ausente o con una huella distinta requiere revisión antes de combinar la prenda.
