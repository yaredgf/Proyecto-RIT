# Constructor Lucene · lectura por líneas

Guía de la versión actual de [ConstructorLucene.java](../../indexadores/lucene/src/main/java/rit/ConstructorLucene.java). Las líneas en blanco separan bloques. Las llaves de cierre aparecen junto a la explicación del bloque que cierran.

Seguiremos una única línea de entrada:

```json
{"doc_id":42,"version_id":7,"tokens":["patch","patch","linux"]}
```

El normalizador preparará esta lista a partir de texto inglés. El constructor lee el arreglo JSON, crea una lista Java y entrega cada elemento a Lucene. Después recorre las listas de apariciones del índice para calcular los pesos.

## Líneas 1–39 · Configuración

| Línea | Explicación |
| --- | --- |
| 1 | Declara el paquete `rit`. El nombre completo de la clase es `rit.ConstructorLucene`. |
| 3 | Importa `JsonFactory`, fábrica de lectores y escritores JSON. |
| 4 | Importa `JsonParser`, que avanza por los elementos de una línea JSON. |
| 5 | Importa `JsonToken`, que distingue objetos, campos, números, cadenas y arreglos. |
| 6 | Importa `IOException` para errores de lectura, escritura y validación de entrada. |
| 7 | Importa `Files` para crear, leer, mover y borrar archivos. |
| 8 | Importa `Path` para representar rutas. |
| 9 | Importa `StandardCopyOption` para solicitar la publicación atómica. |
| 10 | Importa `ArrayList`, la lista que crecerá al leer el arreglo JSON. |
| 11 | Importa `Comparator` para ordenar las rutas durante la limpieza. |
| 12 | Importa `List`, el tipo de la lista de términos. |
| 13 | Importa `TokenStream`, la interfaz que Lucene consume para obtener términos. |
| 14 | Importa el atributo con los caracteres del término actual. |
| 15 | Importa el registro `Document` de Lucene. |
| 16 | Importa `Field`, que usaremos para añadir el contenido indexable. |
| 17 | Importa `FieldType`, que define cómo se indexa el contenido. |
| 18 | Importa `StoredField`, que guarda valores recuperables por documento. |
| 19 | Importa `DirectoryReader` para reabrir el índice escrito. |
| 20 | Importa `IndexOptions` para elegir qué información conservar por término. |
| 21 | Importa `IndexWriter`, que incorpora documentos al índice. |
| 22 | Importa `IndexWriterConfig`, que configura ese escritor. |
| 23 | Importa `MultiTerms`, que expone términos a través de los segmentos. |
| 24 | Importa `PostingsEnum` para recorrer documentos y frecuencias. |
| 25 | Importa `FSDirectory`, el directorio de Lucene en el sistema de archivos. |
| 27 | Declara la clase principal como `final`, sin subclases. |
| 28 | Crea una fábrica JSON reutilizable. |
| 29 | Fija `contenido` como nombre del campo indexado. |
| 30 | Crea la configuración de ese campo. |
| 32 | Abre el bloque estático, que se ejecuta al inicializar la clase. |
| 33 | Indica que el campo se indexa como un flujo de términos. |
| 34 | Conserva los documentos y las frecuencias mediante `DOCS_AND_FREQS`. |
| 35 | Omite las normas internas de Lucene. La norma L2 acordada se escribe en `normas.tsv`. |
| 36–37 | Congela el tipo de campo y cierra el bloque estático. |
| 39 | Define el registro con ID de documento, ID de versión y términos. Sus métodos `docId()`, `versionId()` y `tokens()` recuperan esos valores. |

## Líneas 41–65 · La lista se convierte en un flujo

| Línea | Explicación |
| --- | --- |
| 41 | Declara la clase interna que extiende `TokenStream`. |
| 42 | Guarda la referencia a la lista Java. |
| 43 | Registra el atributo que Lucene leerá en cada llamada. |
| 44 | Declara el cursor del siguiente elemento. |
| 46–48 | El constructor recibe la lista y la asigna a `this.tokens`. |
| 50–54 | Sobrescribe `reset()`. Llama al método padre en la 52 y reinicia el cursor en la 53. |
| 56–57 | Sobrescribe `incrementToken()`, que Lucene llama para pedir el siguiente término. |
| 58–60 | Si el cursor llegó al tamaño de la lista, devuelve `false`. |
| 61 | Limpia el atributo que se usó para el término anterior. |
| 62 | Lee `tokens.get(siguiente)`, escribe ese término en el atributo y avanza el cursor con `++`. |
| 63–65 | Devuelve `true` y cierra el método y la clase interna. |

En el ejemplo, el cursor empieza en 0. Tres llamadas devuelven `true` y escriben `patch`, `patch` y `linux`. La cuarta encuentra el cursor en 3 y devuelve `false`.

## Líneas 67–123 · Construcción y publicación

| Línea | Explicación |
| --- | --- |
| 67–71 | `main` exige dos argumentos. Si falta alguno o sobra, escribe el uso y sale con código 2. |
| 72–73 | Convierte los argumentos a rutas y llama a `construir`. La ruta de salida se vuelve absoluta y se normaliza. |
| 75–78 | Abre el método de construcción y rechaza un destino que ya existe. |
| 79 | Crea una carpeta temporal junto al destino final. |
| 80–81 | Inicia el trabajo y abre el directorio temporal como `FSDirectory`. |
| 82 | Abre la entrada UTF-8 con un lector de texto. |
| 83 | Crea el escritor de Lucene. Los recursos de los bloques `try (...)` se cierran automáticamente. |
| 84–86 | Inicializa el último ID en −1, el número de línea en 0 y declara la variable para el texto leído. |
| 87–88 | Lee una línea. En el ejemplo, el contador sube a 1. El bucle termina cuando la lectura devuelve `null`. |
| 89–90 | Abre el bloque de validación y convierte la línea en una `Entrada` con el método de la 125. |
| 91–94 | Comprueba que el ID sea mayor que el anterior y luego actualiza el valor anterior a 42. |
| 95 | Crea el `Document` vacío de Lucene. |
| 96 | Añade el ID estable 42 como campo almacenado. |
| 97 | Añade la versión 7 como campo almacenado. |
| 98 | Crea el campo `contenido` con `TokensNormalizados` y el tipo definido al inicio. |
| 99 | Entrega el documento al escritor. Lucene consume el flujo descrito en las líneas 41–65. |
| 100–103 | Ante un error de entrada, conserva la causa, añade el número de línea y sale del bucle por excepción. |
| 104–107 | Rechaza un archivo con cero líneas y cierra el escritor y el lector. |
| 108–111 | Abre el índice escrito, llama a `guardarPesos` y cierra el lector y el directorio. |
| 112 | Mueve el directorio temporal completo al destino con `ATOMIC_MOVE`. |
| 113–117 | Si hubo un error, enumera las rutas de la carpeta temporal y las elimina con los descendientes primero. |
| 118–123 | Si falla la limpieza, adjunta ese error al original, relanza el original y cierra el método. |

## Líneas 125–167 · Lectura del JSON

| Línea | Explicación |
| --- | --- |
| 125–127 | Abre un parser sobre la línea y exige que el primer elemento sea `{`. |
| 128–130 | Inicializa los dos IDs en −1 y la lista en `null`, lo que permite detectar campos faltantes. |
| 131–134 | Avanza por los nombres de campos, lee el tipo del valor y elige el caso correspondiente. |
| 135–138 | Valida un entero para `doc_id` y obtiene el valor 42 como `long`. |
| 139–142 | Valida un entero para `version_id` y obtiene el valor 7 como `long`. |
| 143–145 | Reconoce el campo `tokens`, exige `[` y crea una lista vacía. |
| 146 | Avanza hasta el siguiente elemento. El bucle termina al llegar a `]`. |
| 147 | Exige que el elemento sea una cadena JSON. |
| 148 | Obtiene el texto actual, por ejemplo `patch`. |
| 149 | Rechaza un elemento vacío o compuesto solo de espacios en blanco. |
| 150–152 | Añade el texto a la lista y cierra el bucle y el caso. Al terminar, conserva los dos `patch`. |
| 153–155 | Ignora valores de campos desconocidos, incluidos arreglos u objetos anidados, y cierra el recorrido de campos. |
| 156–157 | Exige que se cierre el objeto y termine la línea JSON. |
| 158 | Comprueba que ambos IDs sean no negativos y que la lista esté presente. Un arreglo vacío es válido. |
| 159–161 | Devuelve los tres valores agrupados y cierra el parser y el método. |
| 163–167 | Define `exigir`. Si la condición es falsa, lanza una excepción con el mensaje recibido. |

## Líneas 169–204 · IDF y normas L2

| Línea | Explicación |
| --- | --- |
| 169 | Abre el método que lee el índice y escribe los archivos de pesos. |
| 170 | Obtiene N, aquí 1. |
| 171 | Crea una casilla de acumulación por documento interno. Aquí empieza como `[0.0]`. |
| 172 | Obtiene el vocabulario del campo `contenido`. |
| 173 | Abre `idf.jsonl` con un escritor JSON. |
| 174 | Desactiva el separador automático. Cada registro recibirá un salto de línea explícito. |
| 175–177 | Si hay términos, obtiene el iterador y avanza por el vocabulario. En el ejemplo procesa `linux` y después `patch`. |
| 178 | Obtiene DF. Ambos términos tienen DF 1 porque aparecen en el mismo y único documento. |
| 179 | Calcula `1 + ln((N + 1) / (DF + 1))`. Aquí ambos IDF valen 1. |
| 180 | Abre un objeto JSON en la salida. |
| 181 | Escribe el término decodificado en UTF-8. |
| 182 | Escribe el DF. |
| 183 | Escribe el IDF. |
| 184 | Cierra el objeto JSON. |
| 185 | Escribe un salto de línea. |
| 187 | Obtiene la lista de apariciones del término actual con frecuencias. |
| 188 | Recorre los documentos internos de esa lista hasta que Lucene indica el final. |
| 189 | Multiplica TF por IDF. Para `linux` resulta 1 y para `patch` resulta 2. |
| 190 | Suma el cuadrado del peso a la casilla del documento interno 0. La casilla pasa de 0 a 1 y luego a 5. |
| 191–194 | Cierran los recorridos y el escritor de IDF. |
| 195 | Obtiene el mecanismo de lectura de campos almacenados. |
| 196 | Abre `normas.tsv`. |
| 197 | Escribe el encabezado con columnas separadas por tabulaciones. |
| 198 | Recorre los documentos internos. El documento único tiene número interno 0. |
| 199 | Lee el campo almacenado `doc_id` y recupera el ID estable 42. |
| 200 | Escribe 42 junto a la raíz de su acumulador, aproximadamente 2,236. |
| 201–204 | Cierran el bucle, el archivo de normas, el método y la clase. |

La salida contiene el índice invertido, dos filas en `idf.jsonl` y una fila de datos en `normas.tsv`. El número interno 0 sirve para acceder al acumulador durante esta ejecución. La norma se guarda junto al ID estable 42 para recuperarla después. [Matemáticas](matematicas.md) · [Plan de implementación](diseno.md)
