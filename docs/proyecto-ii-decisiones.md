# Proyecto II · Decisiones de diseño y reparto

## Punto de partida

El Proyecto I aporta el arañado y los textos de la colección. [Integración Propia](../Legacy/IntegracionPropia/app.py) usa Requests y Beautiful Soup y guarda archivos locales. [Integración con Librerías](../IntegracionLibrerias/crawler_rit) usa Scrapy y registra versiones y rutas de texto en PostgreSQL. Ambos arañadores cumplen una función general similar. Su almacenamiento y sus reglas de procesamiento pueden producir colecciones distintas, por lo que la equivalencia de sus salidas requiere verificación.

## Revisión de los arañadores del Proyecto I

**Integración con Librerías.** Es la base mejor preparada para el Proyecto II. Scrapy tiene configuración para respetar `robots.txt` y controlar la concurrencia y la espera por dominio. El código separa la planificación, la extracción y el almacenamiento. PostgreSQL registra las versiones y las rutas de texto, lo que permite identificar qué versión entra en cada corrida y repetir la comparación con la misma colección. [Configuración de descarga](../IntegracionLibrerias/crawler_rit/settings.py#L44-L54) · [Calendarizador](../IntegracionLibrerias/crawler_rit/calendarizador.py#L98) · [Almacenamiento](../IntegracionLibrerias/crawler_rit/almacenamiento.py#L19)

**Integración Propia.** Requests, Beautiful Soup e hilos son una combinación razonable para implementar el arañado. Antes de usar su salida como fuente de la colección, conviene tener en cuenta estos puntos del código actual.

| Hallazgo | Efecto sobre la colección | Referencia |
| --- | --- | --- |
| Los hilos revisan si la lista tiene elementos y llaman a `pop()` en operaciones separadas. | Otro hilo puede consumir el último elemento entre ambas operaciones y provocar un `IndexError`. | [Cola de trabajo](../Legacy/IntegracionPropia/app.py#L120-L128) |
| La llamada a `requests.get()` carece de un tiempo límite explícito. | Una conexión lenta puede dejar un hilo esperando y retrasar el cierre de la ejecución. | [Descarga](../Legacy/IntegracionPropia/app.py#L82-L85) |
| La URL se añade a la lista de visitadas antes de confirmar la descarga. | Si la descarga falla, la URL queda como visitada durante esa ejecución y el filtro impide volver a ponerla en cola. | [Filtro de visitadas](../Legacy/IntegracionPropia/app.py#L59-L66) · [Procesamiento](../Legacy/IntegracionPropia/app.py#L120-L128) |
| El nombre del archivo se calcula descartando los parámetros de consulta. | Dos URLs con la misma ruta y parámetros distintos pueden escribir en el mismo archivo y perder uno de los textos. | [Nombres y escritura de archivos](../Legacy/IntegracionPropia/app.py#L88-L97) |

La revisión fue estática. La equivalencia de las colecciones y la magnitud de estos efectos quedan pendientes de verificar sobre los datos existentes.

## Qué se puede reutilizar y qué falta medir

El repositorio es adaptable al Proyecto II porque ya conserva textos y dispone de lógica para seleccionar documentos vigentes, resolver rutas, conservar identificadores técnicos al tokenizar y generar estadísticas y un TF-IDF con scikit-learn. Esa lógica sirve para preparar la entrada común y como referencia de validación. Para el Proyecto II hay que construir el formato binario propio y el índice Lucene, ambos con ejecución independiente. El índice binario puede usar documentos de cualquiera de los arañadores. [Selección de documentos](../IntegracionLibrerias/crawler_rit/indice.py#L42-L51) · [Construcción TF-IDF](../IntegracionLibrerias/crawler_rit/indice.py#L69-L86)

La capacidad de procesar la colección completa requiere medición. El indexador actual carga el catálogo de documentos en memoria mediante `fetchall()` y construye una matriz dispersa global. Conviene medir el pico de memoria y el tiempo de construcción y evaluar el procesamiento por lotes según los resultados. Para comparar el binario propio con Lucene, usar el mismo inventario de versiones y comprobar primero que ambos reciben los mismos textos. [Carga del catálogo](../IntegracionLibrerias/crawler_rit/indice.py#L42-L51) · [Construcción de la matriz](../IntegracionLibrerias/crawler_rit/indice.py#L79-L84)

## Decisiones que ambos deben acordar

1. **Colección de entrada.** Fijar un inventario con identificador estable, versión y ruta de cada texto. Partir de las versiones vigentes registradas en PostgreSQL. Comprobar si hay documentos de la colección que solo existen en la salida local del arañador propio e incorporarlos al inventario cuando corresponda. Acordar cómo tratar duplicados y conservar la misma instantánea para todas las corridas.
2. **Políticas de normalización.** Probar tres perfiles acumulativos. El A define reglas para fechas, números y nombres y protege códigos CVE, CWE y CAPEC y versiones de productos. El B añade stopwords en inglés y lematización y conserva las negaciones. El C añade sinónimos mediante un tesauro técnico. Definir ejemplos de entrada y salida y justificar cada regla con fuentes bibliográficas.
3. **Modelo vectorial.** Especificar cómo se calculan TF, IDF y la normalización de los vectores. Comprobar que la configuración o implementación de Lucene aplica la ponderación acordada. Validar términos, frecuencias por documento, frecuencias documentales y pesos con un corpus pequeño calculado a mano.
4. **Medición.** Ejecutar ambos programas sobre la misma instantánea y en el mismo equipo. Registrar tiempo de construcción, tamaño total en disco, documentos, vocabulario y memoria máxima. Definir si el tiempo incluye la normalización y aplicar el mismo criterio a ambos índices. Comparar estructuras internas y documentar qué cambia con cada perfil.

## Reparto entre dos personas

| Persona | Implementación y entregables |
| --- | --- |
| 1 · Índice propio | Diseñar el índice invertido y su formato binario, implementar el programa independiente y su archivo de configuración estilo Linux, generar tres binarios y explicar su estructura con un diagrama y una muestra anotada de `hexdump -C`. |
| 2 · Apache Lucene | Implementar el programa independiente con las mismas políticas configurables, generar las tres variantes de Lucene, liderar las mediciones de ambos programas y documentar la estructura interna y la comparación. |
| Ambas | Acordar el inventario, los perfiles, la fórmula y las pruebas. Justificar las decisiones, completar el informe con portada y estadísticas, preparar la defensa oral y empaquetar la entrega en `.tar.gz` con el repositorio Git. |

## Base común y flujo de ramas

Usar **Integración con Librerías** como fuente principal de documentos. Scrapy recopila los textos y PostgreSQL registra sus versiones y rutas. A partir de esos datos, preparar un inventario común e incorporar los documentos únicos de Integración Propia que correspondan a la colección. Fijar una instantánea de ese inventario para las mediciones.

1. En la rama base, registrar en un commit común el formato del inventario, los tres perfiles y sus recursos de normalización, la fórmula TF-IDF y el corpus pequeño de prueba con resultados esperados.
2. Crear **`p2/indice-propio`** y **`p2/lucene`** desde ese mismo commit. La primera rama implementará el programa que genera el binario propio. La segunda implementará el programa que genera el índice con Apache Lucene. Cada programa leerá directamente el inventario común, aplicará los mismos perfiles y escribirá sus propias salidas. Ambos podrán ejecutarse por separado con el arañador detenido, lo que permite desarrollarlos en paralelo o en secuencia.
3. Si cambia un acuerdo compartido durante el desarrollo, actualizarlo en la rama base e incorporar el cambio en ambas ramas.
4. Integrar las dos implementaciones en una rama de entrega y ejecutar la comparación sobre la misma instantánea de la colección completa.

## Cuántos índices preparar

La especificación pide **dos programas indexadores independientes del arañador**. La rúbrica exige **al menos tres archivos de índices con distintas políticas de normalización** y que Lucene implemente las mismas estrategias que el índice propio. Para cubrir ambos puntos y comparar cada perfil en igualdad de condiciones, el plan propone **tres binarios propios y tres directorios Lucene**, generados sobre una sola colección común.

| Salida | Perfil A | Perfil B | Perfil C |
| --- | --- | --- | --- |
| Binario propio | 1 archivo | 1 archivo | 1 archivo |
| Apache Lucene | 1 directorio | 1 directorio | 1 directorio |

La obligación se aplica a los dos indexadores del Proyecto II. La especificación no exige repetir esta matriz por cada arañador del Proyecto I. Cada indexador debe poder ejecutarse por separado en cualquier momento.
