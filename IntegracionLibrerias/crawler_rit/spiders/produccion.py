"""Extiende el spider semillas existente sin duplicar su implementación."""
import json
from pathlib import Path

from crawler_rit.spiders.semillas import SemillasSpider
from crawler_rit.politicas import AccesoDenegado, FinRecopilacion
from crawler_rit.database import conectar
from crawler_rit.mantenimiento import conservar
from crawler_rit.settings import RIT_RUTAS

class ProduccionSpider(SemillasSpider):
    name = 'rit'
    custom_settings = {
        'RETRY_ENABLED': False,
        'REDIRECT_ENABLED': False,
        # La pausa dinámica se aplica en PoliticasMiddleware.
        'DOWNLOAD_DELAY': 0,
        'DOWNLOAD_DELAY_JITTER': 0,
        'ROBOTSTXT_OBEY': True,
        'TELNETCONSOLE_ENABLED': False,
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
            'crawler_rit.politicas.PoliticasMiddleware': 540,
        },
    }

    def __init__(self, duracion_prueba=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consultados = set()
        if duracion_prueba is not None:
            self.calendarizador.duracion = int(duracion_prueba)

    def procesar(self, response):
        self.consultados.add(response.meta['id_documento'])
        self.crawler.stats.set_value('rit/documentos_consultados', len(self.consultados))
        yield from super().procesar(response)

    def procesar_html(self, response, id_doc):
        super().procesar_html(response, id_doc)
        conservar(id_doc)

    def error_descarga(self, fallo):
        id_doc = fallo.request.meta['id_documento']
        self.consultados.add(id_doc)
        self.crawler.stats.set_value('rit/documentos_consultados', len(self.consultados))
        try:
            if fallo.check(AccesoDenegado):
                self.descartar(id_doc, fallo.getErrorMessage())
            elif fallo.check(FinRecopilacion):
                with conectar() as c:
                    c.execute("UPDATE documentos SET estado = 'pendiente' WHERE id = %s", (id_doc,))
            else:
                self.dejar_pendiente(id_doc, fallo.getErrorMessage())
        finally:
            self.calendarizador.liberar(id_doc)
        yield from self.siguientes()

    def closed(self, reason):
        super().closed(reason)
        self.crawler.stats.set_value('rit/motivo_cierre', reason)
        with conectar() as c:
            resumen = c.execute('SELECT estado, COUNT(*) AS cantidad FROM documentos WHERE id_ciclo = %s GROUP BY estado', (self.calendarizador.id_ciclo,)).fetchall()
        self.crawler.stats.set_value('rit/estados_finales', {f['estado']: f['cantidad'] for f in resumen})
        ruta = Path(RIT_RUTAS['logs'])
        ruta.mkdir(parents=True, exist_ok=True)
        (ruta / f'estadisticas_ciclo_{self.calendarizador.id_ciclo}.json').write_text(
            json.dumps(self.crawler.stats.get_stats(), default=str, indent=2), encoding='utf-8')
