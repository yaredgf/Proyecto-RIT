# Consulta Lucene · Implementación paso a paso

## Paso 1. Contar la TF de la consulta

El constructor crea el índice a partir de documentos que ya traen sus términos en JSONL. La consulta abre ese índice y recibe sus propios términos, también previamente normalizados. La TF de la consulta se cuenta sobre los argumentos del comando. La TF de un documento quedó registrada en sus listas de apariciones al construir el índice.

### Código por líneas

Siga el recorrido en [ConsultaLucene.java](../../indexadores/lucene/src/main/java/rit/ConsultaLucene.java). Las líneas en blanco separan bloques.

| Línea | Qué hace |
| --- | --- |
| 1 | Declara el paquete `rit`. El nombre que Maven ejecuta es `rit.ConsultaLucene`. |
| 3 | Importa `IOException` para informar fallos al abrir o leer el índice. |
| 5 | Importa `Path` para representar la ruta del índice. |
| 9 | Importa `LinkedHashMap` para guardar un contador por término en su orden de primera aparición. |
| 10 | Importa `DirectoryReader`, el lector del índice Lucene. |
| 14 | Importa `FSDirectory` para acceder al directorio en disco. |
| 17 | Declara la clase que ejecuta este paso. |
| 18 | Declara `main`, que recibe los argumentos del comando y puede propagar errores de entrada o salida. |
| 19–21 | Exige como mínimo la ruta y un término. Si solo llega la ruta, muestra el mensaje de uso mediante una excepción. |
| 23 | Convierte el argumento 0 en la ruta del índice. |
| 24 | Abre el directorio de Lucene. |
| 25 | Abre el lector del índice existente. El bloque cerrará el lector y después el directorio. |
| 26 | Crea el mapa vacío. Cada clave es un término y su valor es la TF en la consulta. |
| 27 | Inicia el recorrido en el argumento 1. La posición 0 contiene la ruta. |
| 28 | Obtiene el término de la vuelta actual. |
| 29–31 | Rechaza términos vacíos o formados solo por espacios. |
| 32 | `merge` guarda 1 si el término aparece por primera vez. Si ya está presente, `Integer::sum` suma 1 al contador actual. |
| 33 | Termina el bucle al consumir todos los argumentos. |
| 35 | Muestra cuántos documentos contiene el índice. Ese valor será N al calcular el IDF. |
| 36 | Recorre los pares término y TF y escribe cada par separado por una tabulación. |
| 38–39 | Cierran los recursos y el método principal. |

Con `patch patch linux`, la primera llamada a `merge` inserta `patch=1`, la segunda lo cambia a `patch=2` y la tercera inserta `linux=1`. Este paso aún no comprueba si cada término existe en el vocabulario.

### Prueba reproducible

Desde la raíz del proyecto, con Maven y Java 21:

```bash
prueba=$(mktemp -d)
printf '%s\n' '{"doc_id":1,"version_id":1,"tokens":["patch","patch","linux"]}' > "$prueba/tokens.jsonl"

mvn -q -f indexadores/lucene/pom.xml compile exec:java \
  -Dexec.args="$prueba/tokens.jsonl $prueba/indice"

mvn -q -f indexadores/lucene/pom.xml exec:java \
  -Dexec.mainClass=rit.ConsultaLucene \
  -Dexec.args="$prueba/indice patch patch linux"
```

El primer comando Maven usa el constructor por defecto. El segundo selecciona la clase de consulta mediante `-Dexec.mainClass`. Para permitir ambas invocaciones, el POM define la clase predeterminada como propiedad.

Resultado observado con Java 21 y Maven, aparte del aviso de rendimiento de Lucene:

```text
Documentos en el índice: 1
patch   2
linux   1
```

También se comprobó que invocar la consulta con solo la ruta devuelve un error de uso. El [paso 2](#paso-2-preparar-el-vector) añade la resolución del IDF y la normalización del vector. En el código actual, su salida aparece después de estas líneas de diagnóstico. [Plan](diseno.md) · [Matemáticas](matematicas.md)

## Paso 2. Preparar el vector

El paso 1 cuenta las repeticiones de la consulta. El paso 2 pregunta a Lucene cuántos documentos contienen cada término, calcula su peso TF-IDF y divide por la norma L2 de la consulta. La entrada sigue siendo una lista de términos ya normalizados en inglés.

### Líneas añadidas

| Línea | Qué hace |
| --- | --- |
| 13 | Importa `Term`. Un `Term` identifica una palabra dentro de un campo del índice. |
| 37 | Llama al nuevo método después de obtener las TF de la consulta. |
| 41–42 | Declara el método y recibe el lector abierto y las frecuencias. Puede propagar errores de lectura. |
| 43 | Crea un mapa para guardar los pesos TF-IDF antes de normalizar. |
| 44 | Inicializa el acumulador de cuadrados en cero. |
| 45 | Obtiene N, el total de documentos del índice. |
| 46 | Recorre cada par término y frecuencia de la consulta. |
| 47 | Extrae el término de la vuelta actual. |
| 48 | Pregunta por el DF del término en el campo `contenido`. |
| 49–51 | Si el DF es cero, avanza al término siguiente. |
| 52 | Calcula el IDF con la fórmula acordada. |
| 53 | Multiplica la TF de la consulta por el IDF del índice. |
| 54 | Guarda el peso para dividirlo después por la norma común. |
| 55–56 | Suma el cuadrado del peso y termina la vuelta. |
| 58–61 | Si todos los términos quedaron fuera del vocabulario, pide reformular y termina antes de dividir. |
| 63 | Toma la raíz cuadrada de la suma y obtiene la norma L2. |
| 64–65 | Imprime la norma y el encabezado de los pesos. |
| 66 | Divide cada peso entre la norma e imprime el resultado. |
| 67–68 | El método termina en la línea 68. La clase continúa con el paso 3. |

[ConsultaLucene.java](../../indexadores/lucene/src/main/java/rit/ConsultaLucene.java)

### Prueba

Construya el índice pequeño del [paso 1](#paso-1-contar-la-tf-de-la-consulta) y ejecute la misma clase pasando `patch linux linux`:

```bash
mvn -q -f indexadores/lucene/pom.xml compile exec:java \
  -Dexec.mainClass=rit.ConsultaLucene \
  -Dexec.args="$prueba/indice patch linux linux"
```

En el índice de un documento, ambos términos tienen DF 1 e IDF 1. Los pesos sin normalizar son 1 y 2. La línea 55 acumula 1 y luego 5. La línea 63 obtiene la raíz de 5. La línea 66 produce `patch = 0.4472135954999579` y `linux = 0.8944271909999159`. Verifiqué con Java 21 y Maven que coinciden con `1/sqrt(5)` y `2/sqrt(5)`. Una consulta que solo contiene `unknown` produjo el mensaje de reformulación.

El [paso 3](#paso-3-puntuar-y-ordenar-documentos) usa estos pesos para sumar aportes y ordenar documentos. [Plan](diseno.md) · [Matemáticas](matematicas.md)

## Paso 3. Puntuar y ordenar documentos

Dividimos en dos momentos. Primero sumamos `pesoConsultaNormalizado × TFDocumento × IDF` por cada término que el documento comparte con la consulta. Luego dividimos la suma por la norma del documento. Podemos hacer esa división al final porque todos los aportes de un documento usan la misma norma.

### Código por líneas

| Línea de ConsultaLucene.java | Qué hace |
| --- | --- |
| 4, 6–8 | Importan la lectura de archivos, la lista de resultados, el comparador y el mapa de acumulación. |
| 11–12, 15 | Importan el acceso al vocabulario, el recorrido de apariciones y la representación en bytes de un término. |
| 37, 41 | Pasan la ruta del índice al método que prepara el vector para que la puntuación pueda abrir sus normas. |
| 48, 52 | Reutilizan el nombre de campo y el cálculo de IDF del constructor. |
| 67 | Envía los pesos y la norma de la consulta al método que puntúa. |
| 70 | Agrupa el ID estable y el puntaje de un resultado. |
| 72–73 | Declara el método y sus entradas. |
| 74 | Crea el acumulador por número interno de documento. |
| 75 | Abre el iterador de términos del campo indexado. |
| 76–77 | Recorre los términos útiles de la consulta y se posiciona sobre cada uno en Lucene. |
| 78 | Calcula el IDF a partir del DF que devuelve Lucene. |
| 79 | Divide el peso del término en la consulta por su norma. |
| 80 | Obtiene la lista de apariciones del término con sus frecuencias. |
| 81 | Avanza por los documentos de esa lista hasta que se acaba. |
| 82 | Calcula el peso del término en el documento con su TF e IDF. |
| 83–85 | Suma el producto al acumulador del documento y cierra ambos recorridos. |
| 87–89 | Carga las normas, prepara la lectura de campos almacenados y crea la lista de resultados. |
| 90–92 | Por cada documento con aporte, recupera el ID estable y busca su norma. |
| 93–95 | Señala un índice incompleto si falta una norma válida para un documento con coincidencias. |
| 96–97 | Divide el producto acumulado por la norma y agrega el resultado. |
| 99 | Ordena por coseno descendente y luego por ID ascendente. |
| 100–102 | Imprime el encabezado y hasta 50 resultados, y cierra el método. |
| 104–109 | Abre el método de lectura de normas y verifica el encabezado del TSV. |
| 110–115 | Lee cada línea, separa las dos columnas por tabulaciones y comprueba su cantidad. |
| 116–121 | Convierte el ID y la norma, los guarda y detecta IDs duplicados. |
| 122–126 | Convierte un valor numérico ilegible en un error con el contexto de la fila y cierra el archivo. |
| 127–129 | Devuelve las normas y cierra el método y la clase. |

En el constructor, la línea 29 comparte el nombre `contenido` dentro del paquete. La línea 179 llama a `calcularIdf` y las 205–207 implementan la fórmula usada por ambos programas. [ConsultaLucene.java](../../indexadores/lucene/src/main/java/rit/ConsultaLucene.java) · [ConstructorLucene.java](../../indexadores/lucene/src/main/java/rit/ConstructorLucene.java)

### Prueba reproducible

```bash
prueba=$(mktemp -d)
cat > "$prueba/tokens.jsonl" <<'JSONL'
{"doc_id":42,"version_id":1,"tokens":["patch","patch","linux"]}
{"doc_id":84,"version_id":2,"tokens":["patch","windows"]}
{"doc_id":99,"version_id":3,"tokens":["linux","linux","patch"]}
JSONL

mvn -q -f indexadores/lucene/pom.xml compile exec:java \
  -Dexec.args="$prueba/tokens.jsonl $prueba/indice"

mvn -q -f indexadores/lucene/pom.xml exec:java \
  -Dexec.mainClass=rit.ConsultaLucene \
  -Dexec.args="$prueba/indice patch linux unknown"
```

Resultado observado con Java 21. `unknown` se ignora al calcular el vector:

| ID estable | Coseno |
| --- | ---: |
| 99 | 0,9582646897980635 |
| 42 | 0,9432668510216812 |
| 84 | 0,3119172480155738 |

En el documento 84, la línea 83 acumula únicamente el aporte de `patch`. La línea 96 divide por la norma de `patch windows`. También se comprobó que, ante dos puntajes de 1, sale primero el ID menor y un documento sin términos queda fuera del resultado.

Este paso cubre la consulta temática con términos ya normalizados. La entrada desde textos reales en inglés, la paginación y los filtros por códigos corresponden a los próximos pasos. [Plan](diseno.md)
