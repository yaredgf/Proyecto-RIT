package rit;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.FieldType;
import org.apache.lucene.document.StoredField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexOptions;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.MultiTerms;
import org.apache.lucene.index.PostingsEnum;
import org.apache.lucene.store.FSDirectory;

public final class ConstructorLucene {
    private static final JsonFactory JSON = new JsonFactory();
    private static final String CONTENIDO = "contenido";
    private static final FieldType TIPO_CONTENIDO = new FieldType();

    static {
        TIPO_CONTENIDO.setTokenized(true);
        TIPO_CONTENIDO.setIndexOptions(IndexOptions.DOCS_AND_FREQS);
        TIPO_CONTENIDO.setOmitNorms(true);
        TIPO_CONTENIDO.freeze();
    }

    private record Entrada(long docId, long versionId, List<String> tokens) {}

    private static final class TokensNormalizados extends TokenStream {
        private final List<String> tokens;
        private final CharTermAttribute termino = addAttribute(CharTermAttribute.class);
        private int siguiente;

        TokensNormalizados(List<String> tokens) {
            this.tokens = tokens;
        }

        @Override
        public void reset() throws IOException {
            super.reset();
            siguiente = 0;
        }

        @Override
        public boolean incrementToken() {
            if (siguiente == tokens.size()) {
                return false;
            }
            clearAttributes();
            termino.append(tokens.get(siguiente++));
            return true;
        }
    }

    public static void main(String[] argumentos) throws IOException {
        if (argumentos.length != 2) {
            System.err.println("Uso: ConstructorLucene <tokens.jsonl> <directorio-nuevo>");
            System.exit(2);
        }
        construir(Path.of(argumentos[0]), Path.of(argumentos[1]).toAbsolutePath().normalize());
    }

    private static void construir(Path entrada, Path destino) throws IOException {
        if (Files.exists(destino)) {
            throw new IOException("El destino ya existe. Elija un directorio nuevo: " + destino);
        }
        Path temporal = Files.createTempDirectory(destino.getParent(), ".lucene-");
        try {
            try (var directorio = FSDirectory.open(temporal)) {
                try (var lector = Files.newBufferedReader(entrada);
                     var escritor = new IndexWriter(directorio, new IndexWriterConfig())) {
                    long anterior = -1;
                    long numeroLinea = 0;
                    String linea;
                    while ((linea = lector.readLine()) != null) {
                        numeroLinea++;
                        try {
                            Entrada documento = leer(linea);
                            if (documento.docId() <= anterior) {
                                throw new IOException("doc_id debe ser único y estar en orden ascendente");
                            }
                            anterior = documento.docId();
                            var registro = new Document();
                            registro.add(new StoredField("doc_id", documento.docId()));
                            registro.add(new StoredField("version_id", documento.versionId()));
                            registro.add(new Field(CONTENIDO, new TokensNormalizados(documento.tokens()), TIPO_CONTENIDO));
                            escritor.addDocument(registro);
                        } catch (IOException | IllegalArgumentException error) {
                            throw new IOException("Entrada inválida en la línea " + numeroLinea, error);
                        }
                    }
                    if (numeroLinea == 0) {
                        throw new IOException("El flujo de documentos está vacío.");
                    }
                }
                try (var lector = DirectoryReader.open(directorio)) {
                    guardarPesos(lector, temporal);
                }
            }
            Files.move(temporal, destino, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException | RuntimeException error) {
            try (var rutas = Files.walk(temporal)) {
                for (Path ruta : rutas.sorted(Comparator.reverseOrder()).toList()) {
                    Files.delete(ruta);
                }
            } catch (IOException limpieza) {
                error.addSuppressed(limpieza);
            }
            throw error;
        }
    }

    private static Entrada leer(String linea) throws IOException {
        try (JsonParser parser = JSON.createParser(linea)) {
            exigir(parser.nextToken() == JsonToken.START_OBJECT, "Se esperaba un objeto");
            long docId = -1;
            long versionId = -1;
            List<String> tokens = null;
            while (parser.nextToken() == JsonToken.FIELD_NAME) {
                String nombre = parser.currentName();
                JsonToken valor = parser.nextToken();
                switch (nombre) {
                    case "doc_id" -> {
                        exigir(valor == JsonToken.VALUE_NUMBER_INT, "doc_id debe ser entero");
                        docId = parser.getLongValue();
                    }
                    case "version_id" -> {
                        exigir(valor == JsonToken.VALUE_NUMBER_INT, "version_id debe ser entero");
                        versionId = parser.getLongValue();
                    }
                    case "tokens" -> {
                        exigir(valor == JsonToken.START_ARRAY, "tokens debe ser un arreglo");
                        tokens = new ArrayList<>();
                        while (parser.nextToken() != JsonToken.END_ARRAY) {
                            exigir(parser.currentToken() == JsonToken.VALUE_STRING, "Cada token debe ser texto");
                            String termino = parser.getText();
                            exigir(!termino.isBlank(), "Un token no puede estar vacío");
                            tokens.add(termino);
                        }
                    }
                    default -> parser.skipChildren();
                }
            }
            exigir(parser.currentToken() == JsonToken.END_OBJECT && parser.nextToken() == null,
                    "Se esperaba exactamente un objeto por línea");
            exigir(docId >= 0 && versionId >= 0 && tokens != null, "Faltan doc_id, version_id o tokens válidos");
            return new Entrada(docId, versionId, tokens);
        }
    }

    private static void exigir(boolean condicion, String mensaje) throws IOException {
        if (!condicion) {
            throw new IOException(mensaje);
        }
    }

    private static void guardarPesos(DirectoryReader lector, Path destino) throws IOException {
        int totalDocumentos = lector.numDocs();
        double[] cuadrados = new double[totalDocumentos];
        var terminos = MultiTerms.getTerms(lector, CONTENIDO);
        try (var salida = JSON.createGenerator(Files.newOutputStream(destino.resolve("idf.jsonl")))) {
            salida.setRootValueSeparator(null);
            if (terminos != null) {
                var iterador = terminos.iterator();
                for (var termino = iterador.next(); termino != null; termino = iterador.next()) {
                    int df = iterador.docFreq();
                    double idf = 1.0 + Math.log((totalDocumentos + 1.0) / (df + 1.0));
                    salida.writeStartObject();
                    salida.writeStringField("termino", termino.utf8ToString());
                    salida.writeNumberField("df", df);
                    salida.writeNumberField("idf", idf);
                    salida.writeEndObject();
                    salida.writeRaw('\n');

                    var apariciones = iterador.postings(null, PostingsEnum.FREQS);
                    for (int doc = apariciones.nextDoc(); doc != PostingsEnum.NO_MORE_DOCS; doc = apariciones.nextDoc()) {
                        double peso = apariciones.freq() * idf;
                        cuadrados[doc] += peso * peso;
                    }
                }
            }
        }
        var campos = lector.storedFields();
        try (var salida = Files.newBufferedWriter(destino.resolve("normas.tsv"))) {
            salida.write("doc_id\tnorma_l2\n");
            for (int doc = 0; doc < totalDocumentos; doc++) {
                long id = campos.document(doc).getField("doc_id").numericValue().longValue();
                salida.write(id + "\t" + Math.sqrt(cuadrados[doc]) + "\n");
            }
        }
    }
}
