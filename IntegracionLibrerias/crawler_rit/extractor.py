import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawler_rit.inicializar import normalizar_url


PATRON_IDENTIFICADOR = re.compile(
    r"\b(?:CVE-\d{4}-\d{4,}|CWE-\d+|CAPEC-\d+)\b",
    re.IGNORECASE,
)


def extraer(html, url):
    """
    Recibe HTML y la URL final de la página.
    Devuelve texto, enlaces y códigos; no descarga ni guarda archivos.
    """
    soup = BeautifulSoup(html, "html.parser")

    titulo = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else None
    )

    etiqueta_html = soup.find("html")
    idioma_declarado = (
        etiqueta_html.get("lang")
        if etiqueta_html
        else None
    )

    if idioma_declarado:
        idioma_declarado = (
            idioma_declarado.strip().lower().replace("_", "-")
        )

    # Resolver también páginas que declaran una URL base.
    base = soup.find("base", href=True)
    url_base = urljoin(url, base["href"]) if base else url

    # Recoger enlaces antes de retirar menús y navegación.
    enlaces = []
    vistos = set()

    for etiqueta in soup.find_all("a", href=True):
        destino = urljoin(url_base, etiqueta["href"].strip())

        try:
            normalizada, _ = normalizar_url(destino)
        except ValueError:
            continue

        if normalizada not in vistos:
            vistos.add(normalizada)
            enlaces.append(normalizada)

    # Retirar elementos que no aportan texto documental.
    for etiqueta in soup.find_all([
        "script",
        "style",
        "noscript",
        "template",
        "nav",
        "footer",
        "form",
        "svg",
    ]):
        etiqueta.decompose()

    # Selección inicial y genérica del contenido principal.
    principal = (
        soup.find("main")
        or soup.find("article")
        or soup.body
        or soup
    )

    lineas = []

    for linea in principal.get_text(separator="\n").splitlines():
        limpia = " ".join(linea.split())

        if limpia:
            lineas.append(limpia)

    texto = "\n".join(lineas)

    identificadores = sorted({
        coincidencia.upper()
        for coincidencia in PATRON_IDENTIFICADOR.findall(texto)
    })

    hash_texto = hashlib.sha256(
        texto.encode("utf-8")
    ).hexdigest()

    return {
        "titulo": titulo,
        "idioma_declarado": idioma_declarado,
        "texto": texto,
        "hash_texto": hash_texto,
        "enlaces": enlaces,
        "identificadores": identificadores,
        "resultado_extraccion": "correcto" if texto else "vacio",
    }


def url_ficha(codigo):
    """Construye la dirección de una ficha a partir de su código."""
    codigo = codigo.upper()

    if not PATRON_IDENTIFICADOR.fullmatch(codigo):
        raise ValueError(f"Identificador inválido: {codigo}")

    if codigo.startswith("CVE-"):
        return f"https://nvd.nist.gov/vuln/detail/{codigo}"

    numero = codigo.split("-", 1)[1]

    if codigo.startswith("CWE-"):
        return f"https://cwe.mitre.org/data/definitions/{numero}.html"

    return f"https://capec.mitre.org/data/definitions/{numero}.html"