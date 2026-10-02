"""Políticas HTTPS/robots/pausas para una ejecución del arañador Scrapy."""
import asyncio
import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urljoin

from protego import Protego
from scrapy import Request, signals
from scrapy.exceptions import IgnoreRequest
from scrapy.http.request import NO_CALLBACK

from crawler_rit.database import conectar
from crawler_rit.settings import RIT_CONFIG

class AccesoDenegado(IgnoreRequest):
    pass

class FinRecopilacion(IgnoreRequest):
    pass


def espera_retry(valor):
    if not valor:
        return 0
    if isinstance(valor, bytes):
        valor = valor.decode('latin-1')
    valor = valor.strip()
    if valor.isdigit():
        return int(valor)
    try:
        fecha = parsedate_to_datetime(valor)
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return max(0, math.ceil((fecha - datetime.now(timezone.utc)).total_seconds()))
    except (ValueError, TypeError, OverflowError):
        return 0

class PoliticasMiddleware:
    def __init__(self, crawler):
        self.crawler = crawler
        self.cerrojos = {}
        self.robots_cerrojos = {}
        self.activos = set()
        crawler.signals.connect(self.inicio_real, signal=signals.request_reached_downloader)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def sitio(self, url):
        partes = urlsplit(url)
        if partes.scheme != 'https' or partes.username or partes.password or partes.port not in (None, 443):
            raise AccesoDenegado('Solo se permite HTTPS sin credenciales, puerto 443.')
        with conectar() as c:
            fila = c.execute('SELECT * FROM sitios WHERE host = %s', (partes.hostname,)).fetchone()
        if not fila or not fila['permitido']:
            raise AccesoDenegado('Host no autorizado: ' + str(partes.hostname))
        return fila

    def agotado(self):
        cal = getattr(self.crawler.spider, 'calendarizador', None)
        return cal is not None and cal.tiempo_agotado()

    async def robot(self, request):
        host = urlsplit(request.url).hostname
        candado = self.robots_cerrojos.setdefault(host, asyncio.Lock())
        async with candado:
            sitio = self.sitio(request.url)
            fecha = sitio['proxima_revision_robots']
            if fecha and fecha > datetime.now(timezone.utc):
                if sitio['codigo_http_robots'] not in (200, 404, 401, 403):
                    raise IgnoreRequest('Consulta de robots aplazada por un fallo temporal.')
                return Protego.parse(sitio['robots_txt'] or '')
            url = 'https://' + host + '/robots.txt'
            visitadas = set()
            try:
                for salto in range(RIT_CONFIG['descarga']['max_redirecciones'] + 1):
                    self.sitio(url)
                    if url in visitadas:
                        raise IgnoreRequest('Ciclo en redirecciones de robots.txt.')
                    visitadas.add(url)
                    respuesta = await self.crawler.engine.download_async(Request(
                        url, callback=NO_CALLBACK, dont_filter=True,
                        meta={'rit_robots': True, 'dont_retry': True,
                              'dont_redirect': True, 'download_slot': urlsplit(url).hostname}))
                    if respuesta.status not in (301, 302, 303, 307, 308):
                        break
                    if salto == RIT_CONFIG['descarga']['max_redirecciones'] or not respuesta.headers.get(b'Location'):
                        raise IgnoreRequest('Redirección de robots no resoluble.')
                    url = urljoin(url, respuesta.headers[b'Location'].decode('latin-1'))
                codigo = respuesta.status
                if codigo == 200:
                    texto = respuesta.body.decode('utf-8', errors='replace')
                elif codigo == 404:
                    texto = ''
                elif codigo in (401, 403):
                    texto = 'User-agent: *\nDisallow: /\n'
                else:
                    raise IgnoreRequest(f'robots.txt respondió HTTP {codigo}.')
                parser = Protego.parse(texto)
                demora = parser.crawl_delay(RIT_CONFIG['user_agent'])
                with conectar() as c:
                    c.execute('''UPDATE sitios SET robots_txt = %s,
                        codigo_http_robots = %s, fecha_revision_robots = CURRENT_TIMESTAMP,
                        proxima_revision_robots = CURRENT_TIMESTAMP + (%s * INTERVAL '1 hour'),
                        espera_indicada_segundos = %s WHERE host = %s''',
                        (texto, codigo, RIT_CONFIG['robots']['revision_horas'], demora, host))
                return parser
            except Exception:
                with conectar() as c:
                    c.execute('''UPDATE sitios SET robots_txt = NULL,
                        codigo_http_robots = NULL, fecha_revision_robots = CURRENT_TIMESTAMP,
                        proxima_revision_robots = CURRENT_TIMESTAMP + INTERVAL '60 seconds'
                        WHERE host = %s''', (host,))
                raise

    async def process_request(self, request):
        self.sitio(request.url)
        if self.agotado():
            raise FinRecopilacion('Finalizó el período de recopilación.')
        if not request.meta.get('rit_robots') and RIT_CONFIG['robots']['respetar']:
            parser = await self.robot(request)
            if not parser.can_fetch(request.url, RIT_CONFIG['user_agent']):
                raise AccesoDenegado('Acceso prohibido por robots.txt.')
        host = urlsplit(request.url).hostname
        candado = self.cerrojos.setdefault(host, asyncio.Lock())
        await candado.acquire()
        try:
            while True:
                if self.agotado():
                    raise FinRecopilacion('Finalizó el período de recopilación.')
                sitio = self.sitio(request.url)
                siguiente = sitio['proxima_solicitud_permitida']
                espera = (siguiente - datetime.now(timezone.utc)).total_seconds() if siguiente else 0
                if espera <= 0:
                    break
                await asyncio.sleep(min(espera, 1))
            request.meta['download_slot'] = host
            self.activos.add(id(request))
        except BaseException:
            candado.release()
            raise

    def inicio_real(self, request):
        if id(request) not in self.activos:
            return
        sitio = self.sitio(request.url)
        intervalo = RIT_CONFIG['descarga']['intervalo_segundos']
        publicado = sitio['espera_indicada_segundos']
        if publicado is not None:
            intervalo = float(publicado) if RIT_CONFIG['robots']['crawl_delay_reemplaza_intervalo'] else max(intervalo, float(publicado))
        with conectar() as c:
            c.execute('''UPDATE sitios SET ultima_solicitud = CURRENT_TIMESTAMP,
                proxima_solicitud_permitida = CURRENT_TIMESTAMP + (%s * INTERVAL '1 second')
                WHERE host = %s''', (intervalo, sitio['host']))
        self.crawler.stats.inc_value('rit/solicitudes_iniciadas')

    def liberar(self, request):
        if id(request) in self.activos:
            self.activos.remove(id(request))
            self.cerrojos[urlsplit(request.url).hostname].release()

    def process_response(self, request, response):
        try:
            espera = espera_retry(response.headers.get(b'Retry-After'))
            if espera:
                with conectar() as c:
                    c.execute('''UPDATE sitios SET proxima_solicitud_permitida = GREATEST(
                        COALESCE(proxima_solicitud_permitida, CURRENT_TIMESTAMP),
                        CURRENT_TIMESTAMP + (%s * INTERVAL '1 second')) WHERE host = %s''',
                        (espera, urlsplit(request.url).hostname))
            self.crawler.stats.inc_value('rit/bytes_cuerpos_descomprimidos', len(response.body))
            self.crawler.spider.logger.info('HTTP %s %s bytes=%s robots=%s', response.status,
                response.url, len(response.body), bool(request.meta.get('rit_robots')))
            return response
        finally:
            self.liberar(request)

    def process_exception(self, request, exception):
        self.liberar(request)
        self.crawler.spider.logger.warning('Solicitud fallida %s: %s', request.url, exception)
        return None
