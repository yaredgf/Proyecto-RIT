# Lucene · Proyecto II

La colección del proyecto está en inglés. El arañador activo aporta textos de HTML y PDF. El constructor de Lucene ya funciona con documentos previamente normalizados en JSONL y calcula los datos necesarios para la búsqueda temática por coseno.

| Documento | Contenido |
| --- | --- |
| [Diseño y plan de implementación](diseno.md) | Contrato común, decisiones, alcance de cada paso y pruebas de aceptación |
| [Matemáticas con un ejemplo](matematicas.md) | TF, DF, IDF, norma L2, consulta y puntaje de coseno |
| [Constructor línea por línea](constructor-linea-por-linea.md) | Recorrido desde una fila JSONL hasta la publicación del índice |
| [Ejecución del módulo](../../indexadores/lucene/README.md) | Comando con Java y Maven |
| [Decisiones compartidas](../decisiones-tomadas.md) | Reglas que comparten Lucene y el índice binario propio |

## Bitácora

| Avance | Estado y comprobación |
| --- | --- |
| Constructor de Lucene | Implementado. Se probó con entradas válidas, una fila sin términos, una entrada inválida y un destino existente. |
| Cálculo TF-IDF | Implementado. El corpus de tres documentos se ejecutó con Maven y produjo los DF, IDF y normas esperados. |
| Diseño de la consulta temática | Documentado. Falta implementar y probar la recuperación. |
| Inventario, normalizador común e INI | Pendientes. El constructor actual recibe directamente el flujo de términos. |
| Corridas sobre los tres perfiles | Pendientes. Se medirán sobre la misma instantánea que el índice propio. |

Cada avance de código tendrá una entrada en esta bitácora con su objetivo, el enlace a la explicación por líneas, el comando de prueba, el resultado esperado y el resultado observado. Si un cambio desplaza líneas, se actualizará la guía correspondiente.
