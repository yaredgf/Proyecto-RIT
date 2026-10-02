from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException

DetectorFactory.seed = 0


def detectar_idioma(texto):
    if not texto.strip():
        return None

    try:
        # Acotar el texto analizado para reducir el trabajo.
        return detect(texto[:20000])
    except LangDetectException:
        return None