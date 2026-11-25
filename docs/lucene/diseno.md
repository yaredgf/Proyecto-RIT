# Diseño y plan de implementación de Lucene

## Entrada común

Integración con Librerías aporta los textos UTF-8 de la colección en inglés y PostgreSQL conserva sus versiones y rutas. La instantánea común fijará los documentos vigentes y sus huellas antes de las corridas. Lucene recibirá del normalizador compartido una línea JSON por documento con `doc_id`, `version_id` y `tokens`, en orden ascendente de ID. Las repeticiones de términos se conservan porque representan la frecuencia dentro del documento.

Los perfiles pertenecen al normalizador común. A aplica la tokenización y las reglas para fechas, números y nombres, protegiendo códigos y versiones. B añade lematización y stopwords inglesas con excepciones para negaciones. C añade el tesauro. Las consultas temáticas usarán el mismo perfil que el índice al que se dirigen. [Decisiones compartidas](../decisiones-tomadas.md)

## Índice en disco

- `FSDirectory` abre el directorio donde Lucene guarda el índice. Habrá una salida por perfil.
- `TokenStream` entrega los términos preparados por el normalizador. `DOCS_AND_FREQS` conserva los documentos que contienen cada término y sus respectivas frecuencias.
- `doc_id` y `version_id` son campos recuperables. El número interno de Lucene sirve para recorrer apariciones en una generación. El ID estable identifica al documento en el inventario.
- `idf.jsonl` contiene el término, su DF y su IDF. `normas.tsv` guarda el ID estable y la norma L2 del documento. Con esos datos y las frecuencias se pueden reconstruir los pesos normalizados.
- El constructor actual prepara todo en un directorio temporal y lo publica cuando termina. El destino debe ser nuevo.

## Consulta temática propuesta

La primera versión de la consulta recibirá el directorio del índice y una lista de términos ya normalizados para poder probar la matemática por separado. Contará las repeticiones en la consulta, buscará el IDF de los términos que existan y calculará la norma L2 de la consulta. Si ninguno pertenece al vocabulario, pedirá reformular la búsqueda.

Por cada término útil se recorrerá su lista de apariciones. Cada aparición aporta al puntaje del documento el producto del peso normalizado de ese término en la consulta y en el documento. La norma del documento incluye todos sus términos y se recuperará por ID estable. El puntaje usará únicamente el TF-IDF por coseno acordado. Los resultados positivos se ordenarán de mayor a menor, con desempate por ID estable ascendente. El contrato general prevé un máximo de 50 resultados y 10 por página. [Ejemplo matemático](matematicas.md) · [Decisiones compartidas](../decisiones-tomadas.md)

## Pasos para continuar

| Paso | Cambio | Qué se comprobará antes de seguir |
| --- | --- | --- |
| 1 · Leer una consulta | Abrir un índice existente, recibir términos normalizados y contar la TF de cada uno. | `patch patch linux` produce TF 2 para `patch` y TF 1 para `linux`. |
| 2 · Preparar el vector | Resolver el IDF de los términos presentes y dividir sus pesos por la norma L2 de la consulta. | `patch linux` produce aproximadamente 0,613 y 0,790 en el corpus de tres documentos. Una consulta sin términos útiles recibe un mensaje. |
| 3 · Puntuar y ordenar | Recorrer las apariciones, aplicar las normas persistidas y ordenar puntajes. | El documento 3 obtiene cerca de 0,958 y el 2 cerca de 0,312 para `patch linux`. Los empates se resuelven por ID estable. |
| 4 · Conectar la colección real | Integrar el inventario y el normalizador compartido mediante el INI. Aplicar el mismo perfil a documentos y consultas. | Construir primero el perfil A a partir de una instantánea pequeña de textos reales en inglés. |
| 5 · Completar consultas y perfiles | Integrar los filtros por menciones para búsquedas exactas y mixtas y ejecutar los perfiles B y C. | Comprobar que la misma entrada produce los mismos términos y frecuencias en ambos indexadores para cada perfil. |
| 6 · Medir y documentar | Ejecutar ambos indexadores sobre la misma instantánea completa y registrar tiempo, espacio y memoria. | Obtener los tres directorios Lucene y compararlos con los tres binarios propios. |

En cada paso se explicará el cambio antes de programarlo. Después se leerá cada línea añadida o modificada, se seguirá un ejemplo con los valores de las variables y se registrará la prueba.

## Papel de Maven

El `pom.xml` de este módulo se escribió para fijar Java 21, las versiones de Lucene y Jackson y la clase que se ejecuta. Un generador puede crear un POM inicial. Maven lee ese archivo y automatiza la descarga de dependencias, la compilación y la ejecución. [POM del módulo](../../indexadores/lucene/pom.xml)
