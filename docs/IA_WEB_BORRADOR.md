# Asistencia local desde la web

La PR actual es un prototipo de conexión. El botón de Ajustes consulta `GET /api/tags` en `127.0.0.1:11434` cuando se pulsa. La respuesta indica si se encuentran los dos modelos del legado y sus huellas. No descarga modelos y la pantalla todavía no permite analizar fotos ni crear recomendaciones.

Para habilitar una futura conexión desde Pages, Ollama debe estar ejecutándose en el equipo, aceptar el origen HTTPS configurado y el navegador debe permitir el acceso a la red local. El origen de Pages es `https://manuuelmarin.github.io` y se comparte con otros proyectos alojados bajo ese mismo dominio. CORS no distingue sus rutas. Esta relación debe tenerse en cuenta al decidir si conceder acceso al servicio local. No se debe abrir Ollama a la red ni usar un comodín de orígenes para esta integración.

La aplicación Python conserva el contrato de siete grupos en `armario/profiles.py`. Una implementación web completa debe validar el esquema y comprobar foto, huella y revisión antes de aprobar. La propuesta de outfits debe derivarse de prendas activas con perfiles aprobados y vigentes, respetar los filtros y permitir revisión antes de guardar. Tras una inferencia debe volver a comprobar el catálogo. La inferencia local no debe activarse al cargar la página.

El ensayo de conexión en navegador de esta PR intercepta la respuesta de Ollama con datos ficticios. Comprueba el botón, los modelos mostrados y que solo se solicite `/api/tags`. No valida CORS, permisos de red local ni rendimiento de un modelo. Falta un ensayo con Ollama real desde Pages en Chrome y Edge de Windows, y una medición en el equipo de destino.
