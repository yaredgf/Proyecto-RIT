from urllib.parse import urlsplit

from crawler_rit.database import conectar
from crawler_rit.extractor import url_ficha
from crawler_rit.inicializar import normalizar_url


EXTENSIONES_EXCLUIDAS = (
    ".pdf", ".zip", ".gz", ".tar", ".exe", ".msi",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".mp4", ".mp3", ".css", ".js", ".xml", ".json",
)


def registrar_descubrimientos(extraido, url_procedencia):
    nuevas = 0

    with conectar() as conexion:
        filas = conexion.execute(
            "SELECT host FROM sitios WHERE permitido = TRUE"
        ).fetchall()

        hosts = {fila["host"] for fila in filas}

        def registrar(url, tipo=None):
            nonlocal nuevas

            try:
                normalizada, host = normalizar_url(url)
            except ValueError:
                return None

            if host not in hosts:
                return None

            if urlsplit(normalizada).path.lower().endswith(
                EXTENSIONES_EXCLUIDAS
            ):
                return None

            fila = conexion.execute(
                """
                INSERT INTO documentos (
                    url_original, url_normalizada,
                    url_procedencia, tipo, estado
                )
                VALUES (%s, %s, %s, %s, 'pendiente')
                ON CONFLICT (url_normalizada) DO NOTHING
                RETURNING id
                """,
                (url, normalizada, url_procedencia, tipo),
            ).fetchone()

            if fila:
                nuevas += 1
                return fila["id"]

            existente = conexion.execute(
                """
                SELECT id FROM documentos
                WHERE url_normalizada = %s
                """,
                (normalizada,),
            ).fetchone()

            return existente["id"]

        # Primero las fichas, para identificarlas con su tipo.
        for codigo in extraido["identificadores"]:
            direccion = url_ficha(codigo)
            id_ficha = registrar(direccion, "ficha")

            conexion.execute(
                """
                INSERT INTO identificadores (
                    codigo, tipo, url_ficha, id_documento_ficha
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo) DO UPDATE
                SET id_documento_ficha = COALESCE(
                    identificadores.id_documento_ficha,
                    EXCLUDED.id_documento_ficha
                )
                """,
                (
                    codigo,
                    codigo.split("-", 1)[0],
                    direccion,
                    id_ficha,
                ),
            )

        for enlace in extraido["enlaces"]:
            registrar(enlace)

    return nuevas