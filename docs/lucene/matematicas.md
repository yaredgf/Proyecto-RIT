# De las frecuencias al puntaje de búsqueda

## Colección de ejemplo en inglés

| ID | Texto normalizado |
| --- | --- |
| 1 | `patch patch linux` |
| 2 | `patch windows` |
| 3 | `linux linux patch` |

La **TF** cuenta las apariciones del término en un documento concreto. La **DF** cuenta los documentos que contienen el término. **N** es el total de documentos del índice, incluso si alguno queda sin términos después de la normalización. Aquí N vale 3.

| Término | TF en D1 | TF en D2 | TF en D3 | DF | IDF |
| --- | ---: | ---: | ---: | ---: | ---: |
| `patch` | 2 | 1 | 1 | 3 | 1,00000 |
| `linux` | 1 | 0 | 2 | 2 | 1,28768 |
| `windows` | 0 | 1 | 0 | 1 | 1,69315 |

## Construcción

1. Calcular `IDF(t) = 1 + ln((N + 1) / (DF(t) + 1))`. Para `linux`, se obtiene `1 + ln(4/3) ≈ 1,288`.
2. Calcular el peso del término como `TF × IDF`. En D3, `linux` pesa aproximadamente 2,575 y `patch` pesa 1.
3. Sumar los cuadrados de los pesos y tomar la raíz para obtener la norma L2. En D3, `sqrt(2,575364…² + 1²) ≈ 2,763`. En el constructor, las líneas 189 y 190 calculan y acumulan los cuadrados. La 200 escribe la raíz.
4. Para reconstruir un peso normalizado, dividir el peso por la norma del documento. Para D3 se obtiene aproximadamente 0,932 para `linux` y 0,362 para `patch`. Un documento sin términos queda con norma cero.

Si se agrega otro `patch` a D3, su TF pasa de 1 a 2. Su DF y su IDF siguen en 3 y 1, respectivamente. Su aporte cuadrático pasa de 1 a 4 y la norma de D3 sube a aproximadamente 3,261.

## Consulta propuesta

Para `patch linux`, la TF de cada término en la consulta es 1. Se usan los IDF del índice, por lo que los pesos antes de normalizar son 1 y aproximadamente 1,288. La norma de la consulta es `sqrt(1² + 1,287682…²) ≈ 1,630`.

| Término | Peso normalizado en consulta | Peso normalizado en D3 |
| --- | ---: | ---: |
| `patch` | 0,613 | 0,362 |
| `linux` | 0,790 | 0,932 |

El coseno es la suma de los productos de la tabla. Con estos valores redondeados, D3 obtiene `0,613 × 0,362 + 0,790 × 0,932 = 0,958186`. El código usará doble precisión. En D2 solo `patch` aporta a la suma, de modo que obtiene aproximadamente 0,312. `windows` sigue afectando la norma de D2 porque es parte del vector del documento.

La construcción ya produce el IDF y las normas. El recorrido de las listas para puntuar consultas corresponde al siguiente avance. [Diseño de la consulta](diseno.md) · [Fundamentos del modelo vectorial, capítulo 6](https://nlp.stanford.edu/IR-book/html/htmledition/irbook.html)
