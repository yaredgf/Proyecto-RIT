# TheSearcher · Proyecto II · Creación del índice de búsqueda

**Curso** · Recuperación de la Información Textual

## Introducción

El Proyecto I construyó una colección de documentos técnicos en inglés. El Proyecto II construirá dos índices TF-IDF sobre esa colección, uno en un archivo binario diseñado por el equipo y otro con Apache Lucene. Ambos se ejecutarán como programas independientes, incluso con el arañador detenido. El objetivo es medir cuánto espacio ocupa cada índice y cuánto tarda en construirse bajo las mismas políticas de normalización.

## Necesidad de información

La colección reúne avisos, análisis y fichas sobre malware, ransomware y vulnerabilidades de Windows y Linux. Se mantendrán el texto original, su procedencia, las versiones y las menciones CVE, CWE y CAPEC.

## Colectivo al que se dirige

Estudiantes de informática y ciberseguridad, personal de soporte y administradores de Windows y Linux.

## Consultas esperadas

- Recuperar la ficha de un código y los documentos que lo mencionan.
- Buscar análisis temáticos sobre una familia de malware, un producto o una mitigación.
- Combinar códigos con términos temáticos y consultar la procedencia y las versiones conservadas.

## Políticas de indexación y consideraciones de diseño

### Elementos a usar y arquitectura

Integración con Librerías seguirá siendo el arañador activo. Scrapy recopila, PostgreSQL conserva los metadatos y el sistema de archivos guarda los originales HTML o PDF y el texto extraído. Se usará Python para exportar y normalizar la colección y construir el índice propio, y Java con Apache Lucene para el segundo índice. El TF-IDF actual de scikit-learn servirá como referencia del Proyecto I.

Cada comando de construcción recibirá un inventario, un perfil y un destino. Ambos invocarán el mismo normalizador de Python como parte de su ejecución y consumirán en flujo los términos que emita, conservando sus repeticiones. El contrato del flujo será JSON Lines UTF-8 con una fila por documento, `doc_id` y un arreglo de tokens. Cada constructor podrá ejecutarse directamente sobre la instantánea y publicará su salida solo al completarla; una ejecución fallida conservará la generación anterior.

**Justificación.** Una sola implementación de la normalización elimina diferencias accidentales entre lenguajes y permite medir el procesamiento completo de cada índice.

**Configuración.** Usar un archivo INI UTF-8 con secciones `[entrada]`, `[normalizacion]` y `[salida]`. Usar el mismo formato en ambos constructores y guardar las rutas relativas al directorio del INI. Registrar las versiones exactas de Python, Java, Lucene y de los recursos lingüísticos con cada ejecución.

### Colección de entrada y control de duplicados

Exportar todas las versiones vigentes aceptadas de tipo ficha o aviso/análisis. Elegir la versión por fecha de descarga y, en empate, por ID de versión descendente. Revisar los textos históricos de `Legacy/IntegracionPropia/` e incorporar los documentos únicos que cumplan los mismos criterios de idioma, pertinencia y procedencia verificable. Asignar a esas incorporaciones IDs persistentes en un catálogo de importación, sin reutilizar IDs de PostgreSQL.

Congelar una copia de los textos y un inventario JSON Lines UTF-8 ordenado por ID. Verificar SHA-256 sobre los bytes de cada texto y agrupar contenidos idénticos para indexarlos una sola vez. Elegir un representante prefiriendo una ficha oficial y luego el ID menor. Conservar las URLs y versiones del grupo como referencias. Detener la construcción ante un archivo ausente o una huella distinta del inventario. La deduplicación se aplica a la instantánea del índice; la réplica conserva el historial por URL.

**Justificación.** Los dos indexadores reciben las mismas versiones y los duplicados no inflan las frecuencias documentales.

**Metadatos necesarios.** `doc_id`, `version_id`, `ruta_texto`, `sha256`, `url`, `titulo`, `tipo`, `fecha_publicacion`, `fecha_descarga`, `menciones` y referencias de duplicados. Las rutas serán relativas a la instantánea.

### Tokenización, fechas, números y nombres

Conservar el texto fuente legible. Sobre una copia aplicar Unicode NFKC y comparar sin distinguir mayúsculas. Reconocer primero códigos CVE, CWE y CAPEC como tokens indivisibles y conservar puntos, guiones o guiones bajos internos en identificadores técnicos y versiones. Los códigos se guardarán en mayúscula canónica en los metadatos y en minúscula en el índice.

Reconocer fechas completas ISO y fechas con mes inglés explícito, validarlas y emitir `fecha:AAAA-MM-DD`. Las fechas numéricas ambiguas quedan como texto tokenizado. Canonizar números independientes con sintaxis inglesa, eliminando separadores de millares válidos, ceros iniciales y ceros decimales finales. Conservar signo y valor con aritmética decimal. Proteger versiones como `22.04.3` y números unidos a un nombre de producto mediante un vocabulario técnico. Un diccionario de nombres y alias agrupará variantes documentadas, por ejemplo `MS Windows` y `Microsoft Windows` como `microsoft_windows`. Aplicar coincidencia por palabras completas y preferir la coincidencia más larga. Conservar como palabras individuales los nombres fuera del diccionario.

**Justificación.** La canonicalización une variantes de escritura y conserva las distinciones necesarias para buscar códigos, productos y versiones.

### Stopwords, lematización y tesauro

Usar la lista inglesa versionada del Proyecto I y conservar `no`, `not` y `nor`. Proteger también códigos, fechas, números y nombres canonizados. En perfiles con lematización, usar WordNet/Morphy con un diccionario de lemas ingleses congelado para que el resultado sea reproducible. Ante resultados ambiguos, conservar la forma original; las excepciones técnicas y las flexiones con mapeo revisado se guardarán en una tabla común. Conservar stemming desactivado en los tres perfiles. [WordNet, documentación de Morphy](https://wordnet.princeton.edu/documentation/morphy7wn)

El tesauro técnico será un TSV de equivalencias en inglés revisado con ejemplos del corpus. Aplicar la coincidencia más larga sobre las formas ya lematizadas y sustituir cada expresión por una sola forma canónica. Conservar términos con un significado distinto, como `malware` y `ransomware`. Aplicar las mismas reglas al indexar y al preparar consultas.

| Perfil | Política |
| --- | --- |
| A · Básico | Tokenización y canonicalización de códigos, fechas, números y nombres. Conserva stopwords y flexiones. |
| B · Léxico | A, con lematización y eliminación de stopwords sobre las formas resultantes. Conserva negaciones. |
| C · Tesauro | B, con equivalencias del tesauro. La eliminación de stopwords ocurre después de aplicar el tesauro para preservar las expresiones que necesita reconocer. |

**Justificación.** A sirve de referencia, B permite medir el efecto combinado de stopwords y lematización, y C permite aislar el efecto adicional del tesauro.

**Configuración.** Mantener versionados el perfil y los recursos de nombres, versiones, stopwords, lemas y tesauro bajo `config/indexacion/`. La prohibición general de lematizar del Proyecto I pasa a ser la política del perfil A.

### Modelo vectorial clásico

La unidad seguirá siendo el documento completo en su versión vigente. Usar `TF = número de apariciones`, `IDF = 1 + ln((N + 1)/(DF + 1))` y `peso = TF × IDF`, donde `N` incluye todos los documentos únicos aceptados, incluso los que queden sin términos, y `DF` cuenta los documentos con el término en el perfil. Dividir cada peso por la norma L2 de su vector. Un documento sin términos conserva su identificación y un vector vacío. Las consultas ignoran términos fuera del vocabulario y usan el mismo IDF y norma L2. Calcular en doble precisión y comparar con tolerancia absoluta de `1e-6` para pesos y puntuaciones. [Manning, Raghavan y Schütze, capítulos 4 y 6](https://nlp.stanford.edu/IR-book/html/htmledition/irbook.html)

**Justificación.** La ponderación es compatible con el modelo vectorial del Proyecto I y permite comparar ambos índices con una fórmula explícita y un corpus pequeño de referencia.

### Estructura interna del índice binario propio

Usar un único archivo por perfil. La cabecera tendrá la firma ASCII `RITIDX01`, un entero `uint32` con la versión y otro con el perfil (A=1, B=2, C=3). Le seguirán cinco campos `uint64` con el número de documentos, el número de términos y los desplazamientos absolutos de las tablas de documentos, vocabulario y listas de apariciones. Usar orden little-endian y desplazamientos en bytes desde el inicio del archivo.

- **Documentos.** En orden de `doc_id`; cada fila contiene `doc_id` y `version_id` como `uint64` y la norma L2 como `float64`. El ordinal de fila se usa en las listas de apariciones y el inventario aporta la procedencia.
- **Vocabulario.** Términos ordenados por bytes UTF-8. Cada registro contiene una longitud `uint32`, los bytes del término, DF `uint64`, IDF `float64` y el desplazamiento absoluto `uint64` de su lista.
- **Listas de apariciones.** Cada lista contiene exactamente DF pares de enteros ULEB128. El primer entero es la diferencia respecto al ordinal anterior, partiendo de cero para el primer par de cada lista. El segundo es la frecuencia TF. Los ordinales están en orden creciente.

Construir bloques de hasta 250 000 pares término-documento y fusionarlos en disco. Obtener DF e IDF durante la fusión y acumular la norma por ordinal para completar la tabla final. Documentar un ejemplo real con posiciones y valores decodificados mediante `hexdump -C`.

**Justificación.** Guardar únicamente apariciones reales, frecuencias enteras, IDF y normas evita materializar una matriz global y permite recuperar los pesos normalizados con los valores del archivo.

### Estructura interna del índice Lucene

Crear un directorio independiente por perfil con `FSDirectory`. Emitir los términos del normalizador como un `TokenStream` con repeticiones y guardar documentos y frecuencias con `DOCS_AND_FREQS`. Guardar el ID estable y la versión como campos numéricos almacenados y persistir en el directorio los IDF y normas calculados con la misma fórmula, vinculando las normas por ID estable. Usar las listas de apariciones para calcular el producto escalar con el vector de consulta normalizado. La comparación usará la puntuación TF-IDF acordada. BM25 queda fuera de la medición. [Apache Lucene, opciones de indexación](https://lucene.apache.org/core/10_5_2/core/org/apache/lucene/index/IndexOptions.html) · [Apache Lucene, BM25Similarity](https://lucene.apache.org/core/10_5_2/core/org/apache/lucene/search/similarities/BM25Similarity.html)

**Justificación.** Lucene administra segmentos, diccionario y listas; la fórmula acordada permite comparar las salidas con el binario propio. En el informe se describirán las estructuras de los segmentos y las fusiones que se observen en la versión utilizada.

### Análisis de consultas y presentación

Conservar las políticas del Proyecto I. Las búsquedas temáticas en inglés ordenan por coseno positivo, con desempate por ID ascendente, hasta 50 resultados y 10 por página. Una consulta de código exacto usa las menciones y presenta primero la ficha si está disponible. Una consulta mixta exige todos los códigos como filtros y ordena por similitud con los términos restantes. Si la consulta temática queda sin términos útiles, solicitar reformulación. Cada resultado puede mostrar fuente, URL, fecha disponible y menciones, con acceso a versiones históricas. Estas políticas son el contrato de recuperación y se comprobarán por consola con casos de prueba; la entrega del Proyecto II se centra en construir e inspeccionar los índices.

### Validación, estadísticas y entrega

1. Usar un corpus pequeño común que cubra códigos, negaciones, ambigüedad de fechas, nombres, versiones, equivalencias y duplicados. Para comprobar el cálculo, usar dos documentos `patch patch linux` y `patch windows`. En el perfil A, `IDF(patch)=1` y `IDF(linux)=IDF(windows)=1+ln(3/2)`. Para la consulta `patch`, los cosenos esperados son `2/sqrt(4+(1+ln(3/2))²)` y `1/sqrt(1+(1+ln(3/2))²)`, respectivamente.
2. Ejecutar ambos constructores sobre toda la instantánea, con un calentamiento y tres corridas por combinación, alternando el orden, sobre el mismo equipo. Medir desde que empieza la lectura del inventario hasta el cierre exitoso del índice, incluyendo normalización. Usar destinos nuevos y registrar mediana y rango del tiempo y pico de memoria del proceso junto con sus hijos. Medir el tamaño en bytes del binario y la suma de los archivos finales dentro del directorio Lucene, incluidos los datos de ponderación. Registrar tamaño temporal por separado, número de documentos de entrada y únicos, documentos sin términos, vocabulario y número de pares término-documento.
3. Entregar **tres binarios y tres directorios Lucene** sobre la misma colección. Preparar portada con nombre del buscador, integrantes, curso, fecha y título; incluir políticas, estadísticas medidas, diagramas, estructura binaria y evidencia de `hexdump -C`. Empaquetar en `.tar.gz` con el repositorio Git. Ambas personas deben poder defender las dos implementaciones y las políticas de normalización.

### Reparto y flujo de ramas

Registrar en la rama base el contrato, los recursos y el corpus de prueba. Crear `p2/indice-propio` y `p2/lucene` desde el mismo commit. La persona 1 construye el binario, documenta el formato y prepara la demostración con `hexdump -C`. La persona 2 construye el índice Lucene, dirige las mediciones y documenta los resultados comparativos. Si cambia el contrato común, incorporar el cambio en ambas ramas desde la base. Integrar ambas en la rama de entrega y ejecutar allí la comparación definitiva. [Revisión del repositorio y planificación](proyecto-ii-decisiones.md)

## Ampliación de la colección a PDF

Integración con Librerías descubrirá enlaces a PDF en las fuentes autorizadas y aceptará respuestas `application/pdf` o respuestas de tipo genérico con firma PDF. La descarga conserva las reglas de acceso y el límite de tamaño. Poppler extrae la capa textual en UTF-8 y el arañador aplica la misma detección de idioma, filtro temático y detección de códigos que a los HTML. Los PDF escaneados sin capa de texto, protegidos o ilegibles se descartan con motivo registrado. Los PDF no se usan como listados de enlaces.

**Justificación.** Los informes técnicos en PDF amplían la colección con material pertinente. Para el objetivo de 10 GB se cuentan únicamente bytes de texto vigente único, incluidos los extraídos de PDF. Los bytes de los originales se registran por separado. La estadística `GB_decimales_texto_unico` permite comprobar cuánto se ha alcanzado.

**Metadatos necesarios.** Tipo de contenido, ruta del original, ruta del texto, huella SHA-256, bytes, versión y menciones. Se conservan los nombres históricos `ruta_html` y `tamano_html_bytes` en PostgreSQL para los datos del original, sea HTML o PDF.

## Políticas de arañado y almacenamiento heredadas del Proyecto I

Estas decisiones describen la generación y custodia de la colección. La configuración del arañador sigue en JSON y la de los indexadores en INI. Se conserva el ciclo de recolección de seis horas como configuración del arañador; la construcción de cualquiera de los índices del Proyecto II puede iniciarse con una instantánea disponible en cualquier momento.

| Política heredada | Decisión y justificación | Metadatos o configuración |
| --- | --- | --- |
| Formato, idioma y pertinencia | Aceptar HTML y PDF públicos en inglés con texto temáticamente pertinente. Descartar vacíos y extracción insuficiente. Evitar ejecutar JavaScript y descargar recursos de presentación. | Tipo MIME, idioma, resultado y motivo. |
| Semillas y acceso | Conservar las diez semillas configuradas y distinguir listados de documentos. Acceder por HTTPS con certificado válido y aplicar las restricciones de acceso y de cada fuente. | URL, origen, condición de semilla, host y resultado. [Semillas](../config/semillas.txt) |
| Robots y dosificación | Respetar las reglas aplicables de `robots.txt`, sus intervalos y las pausas del servidor. Aplazar ante un fallo temporal al consultar las reglas. Mantener cuatro trabajadores y una solicitud activa por sitio, con intervalo base de tres segundos. La revisión actual de robots es cada 24 horas, dentro del máximo mensual del diseño original. | Reglas, agente, última consulta, próxima revisión, códigos y pausas. |
| Normalización de URLs | Resolver enlaces relativos, retirar fragmentos y parámetros conocidos de rastreo, y preservar parámetros de contenido. Excluir formularios, autenticación, búsquedas internas y combinaciones repetitivas de filtros. | URL original, normalizada, procedencia y motivo de exclusión. |
| Redirecciones y tamaño | Validar el destino en cada salto y cortar ciclos o cadenas de más de cinco saltos. Límite de 10 000 000 bytes de respuesta descomprimida. Descartar contenido parcial por exceso. | Inicio y destino alcanzado, saltos, bytes y resultado. |
| Reintentos | Hasta tres intentos para fallos temporales. El segundo respeta la espera del sitio y el tercero se habilita como mínimo 60 s después del segundo fallo. Aplicar también `Retry-After`. Mantener 30 s como tiempo de espera del descargador. | Intentos, último resultado, siguiente intento y estado final. |
| Cola y reservas | PostgreSQL registra estados, intentos y reservas; el TXT conserva las URLs pendientes según el diseño del Proyecto I. Priorizar la URL elegible más antigua. Reservar antes de descargar, usar transacciones breves y escribir el TXT mediante sustitución de un archivo temporal. Reanudar reservas interrumpidas y conservar pendientes entre ciclos. | URL normalizada, host, estado, incorporación, siguiente intento y ciclo que reservó. |
| Revisitas | Desde la última comprobación satisfactoria, revisar avisos y análisis cada mes y fichas cada dos meses. Encolar revisitas vencidas al iniciar un ciclo. | Tipo, última comprobación y próxima revisión. |
| Extracción | Conservar contenido principal, títulos, párrafos, listas y tablas legibles; retirar navegación repetitiva y guardar UTF-8 con espacios normalizados. | Título, resultado, ruta y bytes del texto. |
| Fichas y menciones | Detectar códigos sin distinguir mayúsculas y registrar una mención por código y versión. Encolar fichas con plantillas configurables y aplicarles las mismas reglas de descarga. Conservar la mención si falla la ficha. La coaparición documenta menciones; las relaciones técnicas requieren evidencia independiente. | Código, tipo, versión, URL de ficha y estado. |
| Control de visitas e historial | Controlar duplicados de URL en la cola y tratar reintentos y revisitas según su calendario. Conservar el original y el texto local, crear versión si cambia la huella SHA-256 y mantener la vigente y hasta dos anteriores. Retirar versiones más antiguas respetando sus referencias. | IDs, fechas, hash, rutas y bytes. |
| Contexto y procedencia | Mantener URL, menciones y fechas en campos separados. Dejar ausente una fecha de publicación desconocida. | Fechas de descarga y publicación. |
| Integridad y separación | Usar PostgreSQL para sitios, ciclos, documentos, versiones, identificadores y menciones, con claves, unicidad, consultas parametrizadas y transacciones breves. Separar originales, texto, índices y bitácoras. Publicar archivos completos antes de actualizar la versión vigente. | [Esquema del repositorio](../sql/001_tablas.sql) · [Configuración del arañador](../config/settingsCrawler.json) |
| Bitácora y volumen | Registrar por ciclo URLs, tiempos, resultados, errores, reintentos y bytes de originales y de texto por separado. Medir el objetivo heredado de 10 GB sobre texto vigente único sin compresión. Detener el arañado al agotar URLs aptas, recibir una orden de detención o sufrir un fallo de almacenamiento. | Identificador del ciclo, inicio, fin, resultado, tamaños y contadores. |
| Comparación de arañadores | Para reproducir una comparación del Proyecto I, ejecutar cada arañador por separado con las mismas semillas, reglas y condiciones de parada. Para el Proyecto II, comparar los indexadores sobre una sola instantánea. | Implementación, entradas, condiciones y resultados. |

El PDF del Proyecto I registra las políticas originales. Las decisiones de implementación anteriores toman como referencia el esquema y la configuración actuales para los parámetros operativos. [Proyecto I, documento de diseño](proyecto-i/Proyecto%20I%20-%20RIT%20-%20Arañador%20y%20repositorio%20de%20información-2.pdf) · [Guía de ejecución](proyecto-i/LEEME_ENTREGA.md)
