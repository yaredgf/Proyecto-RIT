from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from crawler_rit.database import conectar
from crawler_rit.extractor import url_ficha
from crawler_rit.settings import BASE_DIR, RIT_RUTAS


def ruta_repositorio(archivo):
    """
    Guarda una ruta relativa a la raíz del repositorio,
    identificando qué implementación produjo el archivo.
    """
    relativa = archivo.relative_to(BASE_DIR)
    return (Path("IntegracionLibrerias") / relativa).as_posix()


def guardar_documento(
    id_documento,
    html_bytes,
    extraido,
    idioma,
    url_final,
    tipo,
):
    """
    Guarda contenido ya validado y aceptado.

    html_bytes: cuerpo HTML descomprimido, en bytes.
    extraido: resultado de extraer().
    idioma: idioma validado por el procesamiento.
    tipo: 'listado', 'aviso_analisis' o 'ficha'.
    """
    if not extraido["texto"].strip():
        raise ValueError("No se puede guardar una versión sin texto.")

    fecha = datetime.now(timezone.utc)
    archivos_creados = []

    try:
        with conectar() as conexion:
            # Serializa el almacenamiento de versiones del mismo documento.
            documento = conexion.execute(
                """
                SELECT id
                FROM documentos
                WHERE id = %s
                FOR UPDATE
                """,
                (id_documento,),
            ).fetchone()

            if documento is None:
                raise ValueError("El documento no existe.")

            anterior = conexion.execute(
                """
                SELECT id, hash_texto
                FROM versiones
                WHERE id_doc = %s
                ORDER BY fecha_descarga DESC, id DESC
                LIMIT 1
                """,
                (id_documento,),
            ).fetchone()

            nueva_version = (
                anterior is None
                or anterior["hash_texto"] != extraido["hash_texto"]
            )

            if nueva_version:
                nombre = f"{id_documento}_{uuid4().hex}"

                ruta_html = Path(RIT_RUTAS["html"]) / f"{nombre}.html"
                ruta_texto = Path(RIT_RUTAS["texto"]) / f"{nombre}.txt"

                ruta_html.parent.mkdir(parents=True, exist_ok=True)
                ruta_texto.parent.mkdir(parents=True, exist_ok=True)

                texto_bytes = extraido["texto"].encode("utf-8")

                # Registrar las rutas antes de escribir permite limpiar
                # también un archivo cuya escritura haya fallado.
                archivos_creados.append(ruta_html)
                ruta_html.write_bytes(html_bytes)

                archivos_creados.append(ruta_texto)
                ruta_texto.write_bytes(texto_bytes)

                version = conexion.execute(
                    """
                    INSERT INTO versiones (
                        id_doc,
                        fecha_descarga,
                        titulo,
                        idioma,
                        ruta_html,
                        ruta_texto,
                        hash_texto,
                        tamano_html_bytes,
                        tamano_texto_bytes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        id_documento,
                        fecha,
                        extraido["titulo"],
                        idioma,
                        ruta_repositorio(ruta_html),
                        ruta_repositorio(ruta_texto),
                        extraido["hash_texto"],
                        len(html_bytes),
                        len(texto_bytes),
                    ),
                ).fetchone()

                id_version = version["id"]

                for codigo in extraido["identificadores"]:
                    conexion.execute(
                        """
                        INSERT INTO identificadores (
                            codigo, tipo, url_ficha
                        )
                        VALUES (%s, %s, %s)
                        ON CONFLICT (codigo) DO NOTHING
                        """,
                        (
                            codigo,
                            codigo.split("-", 1)[0],
                            url_ficha(codigo),
                        ),
                    )

                    conexion.execute(
                        """
                        INSERT INTO menciones (
                            id_version, codigo_identificador
                        )
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (id_version, codigo),
                    )

            else:
                id_version = anterior["id"]

            conexion.execute(
                """
                UPDATE documentos
                SET estado = 'completada',
                    url_final = %s,
                    tipo = %s,
                    ultima_revision = %s,
                    idioma_detectado = %s,
                    resultado_extraccion = 'correcto',
                    ultimo_error = NULL,
                    motivo_descarte = NULL,
                    proximo_intento = NULL
                WHERE id = %s
                """,
                (url_final, tipo, fecha, idioma, id_documento),
            )

        return {
            "id_version": id_version,
            "nueva_version": nueva_version,
        }

    except Exception:
        # PostgreSQL revierte la transacción. Limpiar los archivos
        # creados durante esta operación sin ocultar el error original.
        for archivo in archivos_creados:
            try:
                archivo.unlink(missing_ok=True)
            except OSError:
                pass

        raise