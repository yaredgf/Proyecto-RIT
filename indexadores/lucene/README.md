# Indexador Lucene · Proyecto II

El constructor lee un flujo UTF-8 de documentos ya normalizados. Por cada fila requiere un `doc_id` único en orden ascendente, su `version_id` y los `tokens`, incluidas las repeticiones. Una fila con cero tokens conserva la versión y genera norma cero. El flujo se mantendrá como interfaz entre el normalizador común y Lucene.

```json
{"doc_id":1,"version_id":1,"tokens":["patch","patch","linux"]}
{"doc_id":2,"version_id":2,"tokens":["patch","windows"]}
```

Con Java 21 o posterior y Maven, desde la raíz del repositorio:

```bash
mvn -f indexadores/lucene/pom.xml compile exec:java \
  -Dexec.args='/tmp/rit-tokens.jsonl /tmp/rit-indice-lucene'
```

El directorio de salida se publica al terminar y debe ser nuevo. Contiene el índice invertido de Lucene, `idf.jsonl` con DF e IDF por término y `normas.tsv` con la norma L2 por ID estable. Las frecuencias se conservan en las listas de apariciones de Lucene.

Este comando permite probar el constructor con un corpus pequeño sin PostgreSQL. El programa que leerá el INI y ejecutará el normalizador común sobre el inventario, la recuperación por coseno y las mediciones de los tres perfiles son etapas posteriores. [Decisiones del Proyecto II](../../docs/decisiones-tomadas.md)
