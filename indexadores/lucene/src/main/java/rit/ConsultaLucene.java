package rit;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.MultiTerms;
import org.apache.lucene.index.PostingsEnum;
import org.apache.lucene.index.Term;
import org.apache.lucene.store.FSDirectory;
import org.apache.lucene.util.BytesRef;

public final class ConsultaLucene {
    public static void main(String[] argumentos) throws IOException {
        if (argumentos.length < 2) {
            throw new IllegalArgumentException("Uso: ConsultaLucene <directorio-indice> <termino>...");
        }

        Path ruta = Path.of(argumentos[0]);
        try (var directorio = FSDirectory.open(ruta);
             var lector = DirectoryReader.open(directorio)) {
            var frecuencias = new LinkedHashMap<String, Integer>();
            for (int i = 1; i < argumentos.length; i++) {
                String termino = argumentos[i];
                if (termino.isBlank()) {
                    throw new IllegalArgumentException("Un término de la consulta no puede estar vacío.");
                }
                frecuencias.merge(termino, 1, Integer::sum);
            }

            System.out.println("Documentos en el índice: " + lector.numDocs());
            frecuencias.forEach((termino, tf) -> System.out.println(termino + "\t" + tf));
            mostrarVectorConsulta(lector, ruta, frecuencias);
        }
    }

    private static void mostrarVectorConsulta(DirectoryReader lector, Path ruta, LinkedHashMap<String, Integer> frecuencias)
            throws IOException {
        var pesos = new LinkedHashMap<String, Double>();
        double sumaCuadrados = 0.0;
        int totalDocumentos = lector.numDocs();
        for (var entrada : frecuencias.entrySet()) {
            String termino = entrada.getKey();
            int df = lector.docFreq(new Term(ConstructorLucene.CONTENIDO, termino));
            if (df == 0) {
                continue;
            }
            double idf = ConstructorLucene.calcularIdf(totalDocumentos, df);
            double peso = entrada.getValue() * idf;
            pesos.put(termino, peso);
            sumaCuadrados += peso * peso;
        }

        if (pesos.isEmpty()) {
            System.out.println("Ningún término está en el vocabulario. Reformule la consulta.");
            return;
        }

        double norma = Math.sqrt(sumaCuadrados);
        System.out.println("Norma L2 de la consulta: " + norma);
        System.out.println("Término\tPeso normalizado");
        pesos.forEach((termino, peso) -> System.out.println(termino + "\t" + (peso / norma)));
        mostrarResultados(lector, ruta, pesos, norma);
    }

    private record Resultado(long id, double coseno) {}

    private static void mostrarResultados(DirectoryReader lector, Path ruta, LinkedHashMap<String, Double> pesos,
                                          double normaConsulta) throws IOException {
        var productos = new HashMap<Integer, Double>();
        var terminos = MultiTerms.getTerms(lector, ConstructorLucene.CONTENIDO).iterator();
        for (var entrada : pesos.entrySet()) {
            terminos.seekExact(new BytesRef(entrada.getKey()));
            double idf = ConstructorLucene.calcularIdf(lector.numDocs(), terminos.docFreq());
            double pesoConsulta = entrada.getValue() / normaConsulta;
            var apariciones = terminos.postings(null, PostingsEnum.FREQS);
            for (int doc = apariciones.nextDoc(); doc != PostingsEnum.NO_MORE_DOCS; doc = apariciones.nextDoc()) {
                double pesoDocumento = apariciones.freq() * idf;
                productos.merge(doc, pesoConsulta * pesoDocumento, Double::sum);
            }
        }

        var normas = leerNormas(ruta.resolve("normas.tsv"));
        var campos = lector.storedFields();
        var resultados = new ArrayList<Resultado>();
        for (var entrada : productos.entrySet()) {
            long id = campos.document(entrada.getKey()).getField("doc_id").numericValue().longValue();
            Double normaDocumento = normas.get(id);
            if (normaDocumento == null || !Double.isFinite(normaDocumento) || normaDocumento <= 0.0) {
                throw new IOException("Norma L2 ausente o inválida para doc_id " + id);
            }
            resultados.add(new Resultado(id, entrada.getValue() / normaDocumento));
        }

        resultados.sort(Comparator.comparingDouble(Resultado::coseno).reversed().thenComparingLong(Resultado::id));
        System.out.println("doc_id\tcoseno");
        resultados.stream().limit(50).forEach(r -> System.out.println(r.id() + "\t" + r.coseno()));
    }

    private static HashMap<Long, Double> leerNormas(Path ruta) throws IOException {
        var normas = new HashMap<Long, Double>();
        try (var lector = Files.newBufferedReader(ruta)) {
            if (!"doc_id\tnorma_l2".equals(lector.readLine())) {
                throw new IOException("Encabezado inválido en " + ruta);
            }
            String linea;
            while ((linea = lector.readLine()) != null) {
                String[] columnas = linea.split("\t", -1);
                if (columnas.length != 2) {
                    throw new IOException("Fila inválida en " + ruta + ": " + linea);
                }
                try {
                    long id = Long.parseLong(columnas[0]);
                    double norma = Double.parseDouble(columnas[1]);
                    if (normas.putIfAbsent(id, norma) != null) {
                        throw new IOException("Norma duplicada para doc_id " + id);
                    }
                } catch (NumberFormatException error) {
                    throw new IOException("Fila inválida en " + ruta + ": " + linea, error);
                }
            }
        }
        return normas;
    }
}
