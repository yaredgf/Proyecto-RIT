# Complemento para la implementación con librerías

Este paquete se copia SOBRE la raíz de Proyecto-RIT. No sustituye la configuración, el SQL, los archivos de datos, el Compose principal ni los módulos que ya escribimos. Añade un spider `rit` basado en el `semillas` actualizado de la conversación.

## Archivos que ya deben existir

- config/settingsCrawler.json y config/semillas.txt.
- IntegracionLibrerias/requirements.txt y scrapy.cfg.
- crawler_rit/settings.py, database.py, inicializar.py, cola.py, calendarizador.py, extractor.py, descubrimiento.py, clasificacion.py, idioma.py, almacenamiento.py.
- crawler_rit/spiders/semillas.py con los ÚLTIMOS cambios: límite de intentos en reservar(), detección de idioma, Retry-After, al_quedar_inactivo(), siguientes() sin self.probadas y con dont_filter=True.
- sql/001_tablas.sql para instalaciones nuevas. Esquema con titulo y nombres snake_case.

## Aplicación

1. Detener cualquier ejecución activa del arañador; no eliminar datos ni volúmenes.
2. Extraer este ZIP en la raíz del proyecto, conservando sus archivos existentes.
3. Ejecutar `bash install.sh` (también desde Fish; no usar `source`).
4. Probar `bash run-librerias.sh --segundos 60`.
5. Revisar logs en IntegracionLibrerias/logs y estadísticas en la generación actual de datos/indice.
6. Ejecutar `bash run-librerias.sh` para la duración indicada por el JSON.

El comando empieza la recopilación y, al terminar o agotar sus URLs, crea el índice. Se detiene la asignación tras el tiempo configurado; una solicitud ya iniciada puede terminar después. No se repiten ciclos indefinidamente. Una nueva ejecución programa las revisitas vencidas y consulta los listados otra vez.

El Dockerfile.final y compose.librerias.yml son complementos. Use siempre los dos archivos Compose al ejecutar manualmente:

```
docker compose -f docker-compose.yml -f compose.librerias.yml run --rm --no-deps crawler_librerias python -m crawler_rit.indice buscar "ransomware windows"
```

Consulta por identificador:

```
docker compose -f docker-compose.yml -f compose.librerias.yml run --rm --no-deps crawler_librerias python -m crawler_rit.indice buscar "CWE-79"
```

Consulta mixta: todos los códigos deben mencionarse en la versión indexada; el resto se ordena por TF-IDF:

```
docker compose -f docker-compose.yml -f compose.librerias.yml run --rm --no-deps crawler_librerias python -m crawler_rit.indice buscar "CWE-79 mitigation" --pagina 1
```

Reconstruir solo el índice:

```
bash run-librerias.sh --solo-indice
```

## Funcionalidad incorporada

- Middleware HTTPS, whitelist exacta por host, robots con Protego, caché PostgreSQL y revisión configurable (24 h por defecto).
- robots 404 permite continuar; 401/403 bloquea; fallos temporales aplazan. Redirecciones de robots limitadas y validadas. No se ignoran fallos de robots para continuar descargando.
- Espera publicada Crawl-delay reemplaza o eleva el intervalo según el JSON. Pausas por host, una descarga activa por host en esta ejecución, Retry-After antes de liberar el host y fecha del inicio registrada.
- Revisitas mensuales/bimensuales usando meses de calendario. Recuperación de reservas de ciclos interrumpidos del arañador con librerías.
- Retención de tres versiones (o valor configurado), eliminación de menciones por cascada, diario de eliminación de archivos.
- Un índice TF-IDF de versiones vigentes, sin stemming ni lematización. Identificadores preservados como tokens. Stopwords inglesas, conservando no/not/nor; install.sh genera el TXT compartido una vez.
- Matriz dispersa float32. Publicación del índice mediante un puntero atómico, conservando generaciones anteriores.
- Búsqueda exacta de códigos, búsqueda mixta y coseno; máximo 50 resultados, páginas de 10, desempate por id_doc. Fragmentos conservados en el índice.
- Estadísticas de texto vigente: documentos, bytes, palabras, palabras distintas, CSV de frecuencias y gráfica PNG. Stopwords incluidas en las estadísticas.
- Logs por ejecución y JSON de métricas de Scrapy por ciclo.
- Instalación que no elimina ni reinicializa tablas existentes. Si falta parte del esquema, se detiene.

## Límites y pruebas necesarias

- No es una entrega validada contra su PostgreSQL ni contra las diez fuentes: ese entorno está en su computadora. Se comprobó sintaxis de Python/Bash y la indexación/búsqueda con un corpus pequeño y una base simulada.
- No ejecutar los dos arañadores simultáneamente todavía: ambos comparten estados. El wrapper usa pg_advisory_lock(43022026); la implementación propia debe adoptar ese mismo bloqueo para impedir ejecuciones concurrentes. Las colas separadas no aíslan los estados compartidos.
- Índice y búsqueda por consola/función Python listos. NO se modifica TheSearcher ni se implementa una API HTTP para Node: la conexión de esa interfaz sigue pendiente.
- TF-IDF fit_transform necesita memoria para el vocabulario y la matriz. No se garantiza que 10 GB de texto quepan en RAM. El requisito de volumen sigue sin demostrarse.
- La extracción genérica y clasificación por términos/rutas siguen siendo heurísticas. Validar manualmente una muestra de documentos y ajustar fuentes. No se garantiza recuperar contenido que requiera JavaScript.
- El cierre de cada ciclo puede tardar más que la ventana de descarga por las solicitudes en curso e indexación.
- Los intentos se cuentan al reservar tareas (como en el código existente), no exclusivamente cuando salen paquetes a la red. Un fallo después de reservar puede consumir un intento.
- El timeout de Scrapy es del descargador; no constituye un límite global de 30 segundos para toda una cadena de redirecciones, robots y espera.
- Las métricas de cuerpos descomprimidos cuentan respuestas completas recibidas, incluido robots. No contabilizan con precisión el cuerpo parcial de una descarga abortada.
- La limpieza de versiones requiere que los archivos de ambas implementaciones sean accesibles. El volumen del complemento monta IntegracionPropia/datos. Si su compañero usa otra ruta, ajustar el volumen o RIT_REPOSITORY_ROOT.
- Los logins, paywalls y páginas de protección no siempre se reconocen automáticamente; deben revisarse los descartes/resultados. No se realiza autenticación ni ejecución de JavaScript.
- Mantener el código y configuración en Git; ignorar datos/logs. No subir modelos, índices, HTML descargado ni .venv.
- Se conservan generaciones anteriores del índice: eliminar manualmente las que no se necesiten SOLO después de comprobar la nueva generación. No se eliminan automáticamente.

## Entrega académica

Separar lo probado de lo propuesto: acompañar la entrega con los logs reales, estadísticas reales, volumen realmente alcanzado y limitaciones. No declarar 10 GB ni integración con la UI si no se alcanzaron.
