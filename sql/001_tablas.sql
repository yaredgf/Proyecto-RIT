BEGIN;

-- 1. Hosts autorizados y reglas de acceso.
CREATE TABLE sitios (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    host TEXT NOT NULL UNIQUE,
    permitido BOOLEAN NOT NULL DEFAULT FALSE,

    robots_txt TEXT,
    fecha_revision_robots TIMESTAMPTZ,
    proxima_revision_robots TIMESTAMPTZ,
    codigo_http_robots INTEGER,

    espera_indicada_segundos NUMERIC,
    ultima_solicitud TIMESTAMPTZ,
    proxima_solicitud_permitida TIMESTAMPTZ,

    CHECK (espera_indicada_segundos >= 0),
    CHECK (codigo_http_robots BETWEEN 100 AND 599)
);


-- 2. Ciclos de recopilación e indexación.
CREATE TABLE ciclos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    implementacion TEXT NOT NULL,
    inicio_recopilacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    fin_recopilacion TIMESTAMPTZ,
    inicio_indexacion TIMESTAMPTZ,
    fin_indexacion TIMESTAMPTZ,

    estado TEXT NOT NULL DEFAULT 'recopilando',

    CHECK (implementacion IN ('propia', 'librerias')),
    CHECK (
        estado IN (
            'recopilando',
            'indexando',
            'completado',
            'interrumpido',
            'fallido'
        )
    )
);


-- 3. URLs administradas por el arañador.
CREATE TABLE documentos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    url_original TEXT NOT NULL,
    url_normalizada TEXT NOT NULL UNIQUE,
    url_final TEXT,
    url_procedencia TEXT,

    fecha_descubrimiento TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    es_semilla BOOLEAN NOT NULL DEFAULT FALSE,

    tipo TEXT,
    estado TEXT NOT NULL DEFAULT 'pendiente',

    intentos INTEGER NOT NULL DEFAULT 0,
    proximo_intento TIMESTAMPTZ,
    ultima_revision TIMESTAMPTZ,
    proxima_revision TIMESTAMPTZ,

    ultimo_codigo_http INTEGER,
    ultimo_error TEXT,
    motivo_descarte TEXT,
    tipo_contenido TEXT,
    idioma_detectado TEXT,
    resultado_extraccion TEXT,

    cantidad_redirecciones INTEGER,
    bytes_ultimo_intento BIGINT,

    id_ciclo BIGINT REFERENCES ciclos(id),

    CHECK (
        tipo IN (
            'listado',
            'aviso_analisis',
            'ficha'
        )
    ),

    CHECK (
        estado IN (
            'pendiente',
            'en_proceso',
            'completada',
            'descartada',
            'fallida'
        )
    ),

    CHECK (intentos >= 0),
    CHECK (cantidad_redirecciones >= 0),
    CHECK (bytes_ultimo_intento >= 0),
    CHECK (ultimo_codigo_http BETWEEN 100 AND 599),

    CHECK (
        resultado_extraccion IN (
            'correcto',
            'vacio',
            'fallido'
        )
    )
);


-- 4. Versiones aceptadas y almacenadas.
CREATE TABLE versiones (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    id_doc BIGINT NOT NULL
        REFERENCES documentos(id) ON DELETE CASCADE,

    fecha_descarga TIMESTAMPTZ NOT NULL,
    titulo TEXT,
    fecha_publicacion TIMESTAMPTZ,
    idioma TEXT NOT NULL,

    ruta_html TEXT NOT NULL,
    ruta_texto TEXT NOT NULL,
    hash_texto VARCHAR(64) NOT NULL,

    tamano_html_bytes BIGINT NOT NULL,
    tamano_texto_bytes BIGINT NOT NULL,

    CHECK (hash_texto ~ '^[0-9a-f]{64}$'),
    CHECK (tamano_html_bytes >= 0),
    CHECK (tamano_texto_bytes >= 0)
);


-- 5. Identificadores y referencia a sus fichas.
CREATE TABLE identificadores (
    codigo TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    url_ficha TEXT NOT NULL,

    id_documento_ficha BIGINT
        REFERENCES documentos(id) ON DELETE SET NULL,

    CHECK (tipo IN ('CVE', 'CWE', 'CAPEC')),

    CHECK (
        (tipo = 'CVE' AND codigo ~ '^CVE-[0-9]{4}-[0-9]{4,}$')
        OR
        (tipo = 'CWE' AND codigo ~ '^CWE-[0-9]+$')
        OR
        (tipo = 'CAPEC' AND codigo ~ '^CAPEC-[0-9]+$')
    )
);


-- 6. Menciones: una relación por versión e identificador.
CREATE TABLE menciones (
    id_version BIGINT NOT NULL
        REFERENCES versiones(id) ON DELETE CASCADE,

    codigo_identificador TEXT NOT NULL
        REFERENCES identificadores(codigo),

    PRIMARY KEY (id_version, codigo_identificador)
);


-- Facilita consultar la versión vigente y el historial.
CREATE INDEX idx_versiones_documento_fecha
    ON versiones (id_doc, fecha_descarga DESC, id DESC);

-- Facilita buscar versiones que mencionan un código.
CREATE INDEX idx_menciones_codigo
    ON menciones (codigo_identificador);

-- Facilita localizar tareas pendientes y sus reintentos.
CREATE INDEX idx_documentos_pendientes
    ON documentos (proximo_intento)
    WHERE estado = 'pendiente';

-- Facilita localizar documentos que requieren revisita.
CREATE INDEX idx_documentos_revision
    ON documentos (proxima_revision)
    WHERE proxima_revision IS NOT NULL;

COMMIT;