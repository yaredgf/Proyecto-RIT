from urllib.parse import urljoin

import scrapy
import math

from crawler_rit.almacenamiento import guardar_documento
from crawler_rit.calendarizador import Calendarizador
from crawler_rit.clasificacion import clasificar
from crawler_rit.database import conectar
from crawler_rit.descubrimiento import registrar_descubrimientos
from crawler_rit.extractor import extraer
from crawler_rit.inicializar import normalizar_url
from crawler_rit.settings import RIT_CONFIG
from crawler_rit.idioma import detectar_idioma
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from scrapy import signals
from scrapy.exceptions import DontCloseSpider


class SemillasSpider(scrapy.Spider):
    name = "semillas"

    custom_settings = {
        # Las redirecciones se controlan explícitamente.
        "REDIRECT_ENABLED": False,
        # Los reintentos completos siguen pendientes de implementar.
        "RETRY_ENABLED": False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calendarizador = Calendarizador()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)

        crawler.signals.connect(
            spider.al_quedar_inactivo,
            signal=signals.spider_idle,
        )

        return spider

    async def start(self):
        self.calendarizador.iniciar()

        for solicitud in self.siguientes():
            yield solicitud

    def siguientes(self):
        if self.calendarizador.tiempo_agotado():
            return

        # Incorporar nuevos documentos y reintentos pendientes.
        self.calendarizador.cola.sincronizar()

        while True:
            tarea = self.calendarizador.reservar()

            if tarea is None:
                return

            yield scrapy.Request(
                url=tarea["url"],
                callback=self.procesar,
                errback=self.error_descarga,
                dont_filter=True,
                meta={
                    "id_documento": tarea["id"],
                    "handle_httpstatus_all": True,
                    "recorrido": [tarea["url"]],
                },
            )

    def dejar_pendiente(self, id_doc, mensaje, espera_minima=0):
        limite = RIT_CONFIG["descarga"]["intentos_totales"]
        espera_final = RIT_CONFIG["descarga"][
            "espera_ultimo_intento_segundos"
        ]

        with conectar() as conexion:
            documento = conexion.execute(
                """
                SELECT intentos
                FROM documentos
                WHERE id = %s
                FOR UPDATE
                """,
                (id_doc,),
            ).fetchone()

            if documento is None:
                raise ValueError(f"No existe el documento {id_doc}.")

            intentos = documento["intentos"]

            if intentos >= limite:
                conexion.execute(
                    """
                    UPDATE documentos
                    SET estado = 'fallida',
                        ultimo_error = %s,
                        proximo_intento = NULL
                    WHERE id = %s
                    """,
                    (str(mensaje)[:1000], id_doc),
                )

                self.logger.error(
                    "Documento %s fallido tras %s intentos: %s",
                    id_doc,
                    intentos,
                    mensaje,
                )
                return

            # Antes del último intento, esperar al menos 60 segundos.
            espera = (
                espera_final
                if intentos == limite - 1
                else 0
            )
            espera = max(espera, espera_minima)

            conexion.execute(
                """
                UPDATE documentos
                SET estado = 'pendiente',
                    ultimo_error = %s,
                    proximo_intento = CURRENT_TIMESTAMP
                        + (%s * INTERVAL '1 second')
                WHERE id = %s
                """,
                (str(mensaje)[:1000], espera, id_doc),
            )

        self.logger.warning(
            "Documento %s: intento %s/%s; espera mínima %s s; %s",
            id_doc,
            intentos,
            limite,
            espera,
            mensaje,
        )

    def descartar(self, id_doc, motivo, resultado=None):
        idioma = None
        extraccion = None

        if resultado is not None:
            idioma = resultado["idioma_declarado"]
            extraccion = resultado["resultado_extraccion"]

        with conectar() as conexion:
            conexion.execute(
                """
                UPDATE documentos
                SET estado = 'descartada',
                    motivo_descarte = %s,
                    idioma_detectado = %s,
                    resultado_extraccion = %s,
                    ultimo_error = NULL,
                    proximo_intento = NULL
                WHERE id = %s
                """,
                (motivo, idioma, extraccion, id_doc),
            )

        self.logger.info(
            "Documento %s descartado: %s",
            id_doc,
            motivo,
        )

    def redireccion(self, response):
        recorrido = response.meta.get(
            "recorrido", [response.request.url]
        )

        maximo = RIT_CONFIG["descarga"]["max_redirecciones"]

        if len(recorrido) - 1 >= maximo:
            raise ValueError("Se superó el máximo de redirecciones.")

        location = response.headers.get(b"Location")

        if not location:
            raise ValueError("Redirección sin cabecera Location.")

        destino = urljoin(
            response.url,
            location.decode("latin-1"),
        )
        destino, host = normalizar_url(destino)

        if destino in recorrido:
            raise ValueError("Se detectó un ciclo de redirecciones.")

        with conectar() as conexion:
            sitio = conexion.execute(
                "SELECT permitido FROM sitios WHERE host = %s",
                (host,),
            ).fetchone()

        if not sitio or not sitio["permitido"]:
            raise ValueError(
                f"Host de redirección no autorizado: {host}"
            )

        return response.request.replace(
            url=destino,
            meta={
                "id_documento": response.meta["id_documento"],
                "handle_httpstatus_all": True,
                "recorrido": recorrido + [destino],
                "download_slot": host,
            },
            dont_filter=True,
        )

    def procesar(self, response):
        id_doc = response.meta["id_documento"]
        recorrido = response.meta.get(
            "recorrido", [response.request.url]
        )
        cantidad_redirecciones = len(recorrido) - 1

        if response.status in (301, 302, 303, 307, 308):
            try:
                with conectar() as conexion:
                    conexion.execute(
                        """
                        UPDATE documentos
                        SET ultimo_codigo_http = %s,
                            url_final = %s,
                            cantidad_redirecciones = %s
                        WHERE id = %s
                        """,
                        (
                            response.status,
                            response.url,
                            cantidad_redirecciones,
                            id_doc,
                        ),
                    )

                siguiente = self.redireccion(response)

            except ValueError as error:
                try:
                    self.descartar(id_doc, str(error))
                finally:
                    self.calendarizador.liberar(id_doc)

                yield from self.siguientes()

            except Exception as error:
                self.logger.exception(
                    "Error procesando redirección: %s",
                    response.url,
                )

                try:
                    self.dejar_pendiente(id_doc, str(error))
                finally:
                    self.calendarizador.liberar(id_doc)

                yield from self.siguientes()

            else:
                # La reserva continúa hasta recibir el destino.
                yield siguiente

            return

        try:
            contenido = response.headers.get(
                b"Content-Type", b""
            ).decode("latin-1").split(";", 1)[0].strip().lower()

            with conectar() as conexion:
                conexion.execute(
                    """
                    UPDATE documentos
                    SET ultimo_codigo_http = %s,
                        url_final = %s,
                        tipo_contenido = %s,
                        bytes_ultimo_intento = %s,
                        cantidad_redirecciones = %s
                    WHERE id = %s
                    """,
                    (
                        response.status,
                        response.url,
                        contenido,
                        len(response.body),
                        cantidad_redirecciones,
                        id_doc,
                    ),
                )

            if response.status in (408, 429, 500, 502, 503, 504):
                espera = self.aplicar_retry_after(response)

                self.dejar_pendiente(
                    id_doc,
                    f"Error HTTP temporal: {response.status}",
                    espera_minima=espera,
                )

            elif response.status != 200:
                self.descartar(
                    id_doc,
                    f"Respuesta HTTP no admitida: {response.status}",
                )

            elif contenido not in (
                "text/html",
                "application/xhtml+xml",
            ):
                self.descartar(
                    id_doc,
                    f"Tipo de contenido no admitido: {contenido}",
                )

            else:
                self.procesar_html(response, id_doc)

        except Exception as error:
            self.logger.exception(
                "Error procesando %s",
                response.url,
            )
            self.dejar_pendiente(id_doc, str(error))

        finally:
            self.calendarizador.liberar(id_doc)

        yield from self.siguientes()

    def procesar_html(self, response, id_doc):
        resultado = extraer(response.text, response.url)

        if not resultado["texto"]:
            self.dejar_pendiente(
                id_doc,
                "Texto extraído vacío.",
            )
            return

        tipo, motivo = clasificar(response.url, resultado)

        if tipo is None:
            self.descartar(id_doc, motivo, resultado)
            return

        if tipo == "listado":
            nuevas = registrar_descubrimientos(
                resultado,
                response.url,
            )

            with conectar() as conexion:
                conexion.execute(
                    """
                    UPDATE documentos
                    SET estado = 'completada',
                        tipo = 'listado',
                        ultima_revision = CURRENT_TIMESTAMP,
                        resultado_extraccion = 'correcto',
                        ultimo_error = NULL,
                        motivo_descarte = NULL,
                        proximo_intento = NULL
                    WHERE id = %s
                    """,
                    (id_doc,),
                )

            self.logger.info(
                "Listado consultado: %s; URLs nuevas: %s",
                response.url,
                nuevas,
            )
            return

        idioma = detectar_idioma(resultado["texto"])
        idioma_objetivo = RIT_CONFIG["coleccion"]["idioma"]

        if idioma != idioma_objetivo:
            motivo = (
                f"Idioma no admitido: {idioma}"
                if idioma
                else "No se pudo determinar el idioma."
            )

            self.descartar(id_doc, motivo, resultado)

            with conectar() as conexion:
                conexion.execute(
                    """
                    UPDATE documentos
                    SET idioma_detectado = %s
                    WHERE id = %s
                    """,
                    (idioma, id_doc),
                )

            return

        guardado = guardar_documento(
            id_documento=id_doc,
            html_bytes=response.body,
            extraido=resultado,
            idioma=idioma,
            url_final=response.url,
            tipo=tipo,
        )

        nuevas = registrar_descubrimientos(
            resultado,
            response.url,
        )

        self.logger.info(
            "Documento guardado: %s; tipo: %s; versión: %s; "
            "nueva versión: %s; URLs nuevas: %s",
            response.url,
            tipo,
            guardado["id_version"],
            guardado["nueva_version"],
            nuevas,
        )

    def error_descarga(self, fallo):
        id_doc = fallo.request.meta["id_documento"]

        try:
            self.dejar_pendiente(
                id_doc,
                fallo.getErrorMessage(),
            )
        finally:
            self.calendarizador.liberar(id_doc)

        yield from self.siguientes()

    def closed(self, reason):
        id_ciclo = self.calendarizador.id_ciclo

        if id_ciclo is None:
            return

        with conectar() as conexion:
            conexion.execute(
                """
                UPDATE documentos
                SET estado = 'pendiente'
                WHERE id_ciclo = %s
                  AND estado = 'en_proceso'
                """,
                (id_ciclo,),
            )

            # Todavía no se ejecuta la fase de indexación.
            conexion.execute(
                """
                UPDATE ciclos
                SET fin_recopilacion = CURRENT_TIMESTAMP,
                    estado = 'interrumpido'
                WHERE id = %s
                """,
                (id_ciclo,),
            )

        self.calendarizador.cola.sincronizar()
    
    def hay_pendientes_autorizadas(self):
        limite = RIT_CONFIG["descarga"]["intentos_totales"]

        with conectar() as conexion:
            hosts = {
                fila["host"]
                for fila in conexion.execute(
                    "SELECT host FROM sitios WHERE permitido = TRUE"
                ).fetchall()
            }

            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT url_normalizada
                    FROM documentos
                    WHERE estado = 'pendiente'
                      AND intentos < %s
                    """,
                    (limite,),
                )

                for fila in cursor:
                    host = urlsplit(fila["url_normalizada"]).hostname

                    if host in hosts:
                        return True

        return False

    def al_quedar_inactivo(self):
        if self.calendarizador.id_ciclo is None:
            return

        if self.calendarizador.tiempo_agotado():
            return

        enviadas = False

        for solicitud in self.siguientes():
            self.crawler.engine.crawl(solicitud)
            enviadas = True

        if enviadas or self.hay_pendientes_autorizadas():
            # Mantener el spider abierto cuando las tareas están
            # esperando su próximo intento o la pausa del host.
            raise DontCloseSpider

    def aplicar_retry_after(self, response):
        cabecera = response.headers.get(b"Retry-After")

        if not cabecera:
            return 0

        valor = cabecera.decode("latin-1").strip()
        ahora = datetime.now(timezone.utc)

        try:
            if valor.isdigit():
                segundos = int(valor)
            else:
                fecha = parsedate_to_datetime(valor)

                if fecha.tzinfo is None:
                    fecha = fecha.replace(tzinfo=timezone.utc)

                segundos = max(
                    0,
                    math.ceil((fecha - ahora).total_seconds()),
                )

        except (ValueError, TypeError, OverflowError):
            self.logger.warning(
                "Retry-After inválido en %s: %s",
                response.url,
                valor,
            )
            return 0

        host = urlsplit(response.url).hostname

        with conectar() as conexion:
            conexion.execute(
                """
                UPDATE sitios
                SET proxima_solicitud_permitida = GREATEST(
                    COALESCE(
                        proxima_solicitud_permitida,
                        CURRENT_TIMESTAMP
                    ),
                    CURRENT_TIMESTAMP
                        + (%s * INTERVAL '1 second')
                )
                WHERE host = %s
                """,
                (segundos, host),
            )

        return segundos