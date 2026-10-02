import re
from urllib.parse import urlsplit

from crawler_rit.inicializar import leer_semillas, normalizar_url
from crawler_rit.settings import RIT_CONFIG


FICHAS = {
    "cwe.mitre.org": r"/data/definitions/\d+\.html",
    "capec.mitre.org": r"/data/definitions/\d+\.html",
    "nvd.nist.gov": r"/vuln/detail/CVE-\d{4}-\d+",
}


def es_ficha(url):
    partes = urlsplit(url)
    patron = FICHAS.get(partes.hostname)

    return bool(
        patron
        and re.fullmatch(patron, partes.path, re.IGNORECASE)
    )


# Las semillas que no son fichas son nuestros listados iniciales.
LISTADOS = set()

for _, url, _ in leer_semillas():
    if not es_ficha(url):
        partes = urlsplit(url)
        LISTADOS.add((partes.hostname, partes.path.rstrip("/")))


def clasificar(url, extraido):
    """
    Devuelve (tipo, motivo_descarte).
    Si tipo es None, la página se descarta.
    """
    normalizada, host = normalizar_url(url)
    partes = urlsplit(normalizada)

    segmentos = {
        segmento.casefold()
        for segmento in partes.path.split("/")
        if segmento
    }

    excluidos = {
        segmento.strip().casefold()
        for segmento in RIT_CONFIG["filtros"]["segmentos_excluidos"]
    }

    if segmentos & excluidos:
        return None, "Ruta excluida por la configuración."

    if es_ficha(normalizada):
        return "ficha", None

    # Las variantes de consulta de un listado, como ?page=2,
    # siguen siendo listados.
    if (host, partes.path.rstrip("/")) in LISTADOS:
        return "listado", None

    contenido = (
        (extraido["titulo"] or "") + "\n" + extraido["texto"]
    ).casefold()

    for termino in RIT_CONFIG["filtros"]["terminos"]:
        patron = r"\b" + re.escape(termino.casefold()) + r"\b"

        if re.search(patron, contenido):
            return "aviso_analisis", None

    return None, "No se encontraron términos del tema."