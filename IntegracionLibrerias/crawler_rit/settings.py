# Scrapy settings for crawler_rit project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import json
import os
from pathlib import Path

# Carpeta IntegracionLibrerias.
BASE_DIR = Path(__file__).resolve().parent.parent

# Raíz de Proyecto-RIT.
PROJECT_ROOT = BASE_DIR.parent

# Permite indicar otra ubicación desde Docker Compose.
CONFIG_PATH = Path(
    os.getenv(
        "RIT_CONFIG_PATH",
        str(PROJECT_ROOT / "config" / "settingsCrawler.json")
    )
).resolve()

with CONFIG_PATH.open(encoding="utf-8") as archivo:
    CONFIG = json.load(archivo)

descarga = CONFIG["descarga"]

BOT_NAME = "crawler_rit"
SPIDER_MODULES = ["crawler_rit.spiders"]
NEWSPIDER_MODULE = "crawler_rit.spiders"

USER_AGENT = CONFIG["user_agent"]


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "crawler_rit (+http://www.yourdomain.com)"

# Obey robots.txt rules
# Permisos de acceso.
ROBOTSTXT_OBEY = CONFIG["robots"]["respetar"]

# Concurrency and throttling settings
#CONCURRENT_REQUESTS = 16
# Concurrencia y frecuencia.
CONCURRENT_REQUESTS = descarga["concurrencia_total"]
CONCURRENT_REQUESTS_PER_DOMAIN = descarga["concurrencia_por_host"]
CONCURRENT_REQUESTS_PER_IP = 0

DOWNLOAD_DELAY = descarga["intervalo_segundos"]
DOWNLOAD_DELAY_JITTER = 0
AUTOTHROTTLE_ENABLED = False

# Límites de descarga.
DOWNLOAD_TIMEOUT = descarga["timeout_segundos"]
DOWNLOAD_MAXSIZE = descarga["max_bytes"]
DOWNLOAD_VERIFY_CERTIFICATES = True

# Solo descargas mediante HTTPS.
DOWNLOAD_HANDLERS = {
    "http": None,
    "ftp": None,
    "file": None,
    "data": None,
    "s3": None,
}

# Redirecciones HTTP.
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = descarga["max_redirecciones"]
METAREFRESH_ENABLED = False

# Scrapy cuenta reintentos adicionales al intento inicial.
RETRY_ENABLED = True
RETRY_TIMES = descarga["intentos_totales"] - 1

COOKIES_ENABLED = False

# Registro inicial por consola.
LOG_LEVEL = "INFO"
LOGSTATS_INTERVAL = 60

FEED_EXPORT_ENCODING = "utf-8"

# Configuración disponible para los componentes que programaremos.
RIT_CONFIG = CONFIG

RIT_RUTAS = {
    nombre: str((BASE_DIR / ruta).resolve())
    for nombre, ruta in CONFIG["rutas"].items()
}

# Docker Compose podrá sustituir estos valores.
RIT_POSTGRES = {
    "host": os.getenv("PGHOST", CONFIG["postgres"]["host"]),
    "port": int(os.getenv("PGPORT", CONFIG["postgres"]["port"])),
    "dbname": os.getenv("PGDATABASE", CONFIG["postgres"]["dbname"]),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
}

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "crawler_rit.middlewares.CrawlerRitSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "crawler_rit.middlewares.CrawlerRitDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    "crawler_rit.pipelines.CrawlerRitPipeline": 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
# FEED_EXPORT_ENCODING = "utf-8"
