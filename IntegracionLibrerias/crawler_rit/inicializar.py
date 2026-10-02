from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from crawler_rit.database import conectar
from crawler_rit.settings import RIT_RUTAS


def normalizar_url(url):
    """Normalización inicial: host en minúsculas y sin fragmento."""
    partes = urlsplit(url)

    if partes.scheme.lower() != "https" or not partes.hostname:
        raise ValueError(f"La semilla debe ser una URL HTTPS: {url}")

    if partes.username is not None or partes.password is not None:
        raise ValueError(f"La URL no debe incluir credenciales: {url}")

    host = partes.hostname.lower().encode("idna").decode("ascii")
    puerto = partes.port

    # Corchetes para direcciones IPv6.
    autoridad = f"[{host}]" if ":" in host else host

    if puerto is not None and puerto != 443:
        autoridad = f"{autoridad}:{puerto}"

    normalizada = urlunsplit((
        "https",
        autoridad,
        partes.path or "/",
        partes.query,
        "",
    ))

    return normalizada, host


def leer_semillas():
    ruta = Path(RIT_RUTAS["semillas"])

    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo de semillas: {ruta}")

    semillas = []
    vistas = set()

    for numero, linea in enumerate(
        ruta.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        original = linea.strip()

        if not original or original.startswith("#"):
            continue

        try:
            normalizada, host = normalizar_url(original)
        except ValueError as error:
            raise ValueError(f"{ruta}, línea {numero}: {error}") from error

        if normalizada not in vistas:
            vistas.add(normalizada)
            semillas.append((original, normalizada, host))

    if not semillas:
        raise ValueError("El archivo de semillas está vacío.")

    return semillas


def inicializar():
    # Validar todas las semillas antes de modificar la base.
    semillas = leer_semillas()
    nuevas = 0

    with conectar() as conexion:
        for original, normalizada, host in semillas:
            # Una semilla configurada por nosotros autoriza su host.
            # Si ya existe, conservamos su autorización actual.
            conexion.execute(
                """
                INSERT INTO sitios (host, permitido)
                VALUES (%s, TRUE)
                ON CONFLICT (host) DO NOTHING
                """,
                (host,),
            )

            sitio = conexion.execute(
                "SELECT permitido FROM sitios WHERE host = %s",
                (host,),
            ).fetchone()

            if not sitio["permitido"]:
                print(f"Semilla omitida: host deshabilitado ({host})")
                continue

            resultado = conexion.execute(
                """
                INSERT INTO documentos (
                    url_original,
                    url_normalizada,
                    es_semilla,
                    estado
                )
                VALUES (%s, %s, TRUE, 'pendiente')
                ON CONFLICT (url_normalizada) DO NOTHING
                RETURNING id
                """,
                (original, normalizada),
            ).fetchone()

            if resultado is not None:
                nuevas += 1
            else:
                # Identificarla como semilla sin reiniciar su estado.
                conexion.execute(
                    """
                    UPDATE documentos
                    SET es_semilla = TRUE
                    WHERE url_normalizada = %s
                    """,
                    (normalizada,),
                )

    # Crear carpetas sin borrar contenido existente.
    for nombre in ("html", "texto", "indice", "logs"):
        Path(RIT_RUTAS[nombre]).mkdir(parents=True, exist_ok=True)

    Path(RIT_RUTAS["cola"]).parent.mkdir(parents=True, exist_ok=True)

    print(f"Semillas únicas leídas: {len(semillas)}")
    print(f"Documentos nuevos registrados: {nuevas}")


if __name__ == "__main__":
    inicializar()