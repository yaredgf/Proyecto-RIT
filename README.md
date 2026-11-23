# Proyecto RIT

La implementación activa usa Scrapy para recopilar la colección, PostgreSQL para sus metadatos y archivos locales para el texto. El Proyecto II usará esa colección como entrada para sus dos indexadores.

| Ruta | Contenido |
| --- | --- |
| [IntegracionLibrerias/](IntegracionLibrerias/) | Arañador activo e indexador TF-IDF del Proyecto I |
| [TheSearcher/](TheSearcher/) | Interfaz web |
| [config/](config/) | Configuración del arañador, semillas y stopwords |
| [sql/](sql/) | Esquema de PostgreSQL |
| [docs/](docs/) | Decisiones del Proyecto II y documentación del Proyecto I |
| [Legacy/](Legacy/) | Implementación propia archivada y sus archivos |
| [textoplano/](textoplano/) | Espacio para la colección original de texto plano |

## Arranque

Desde la raíz del repositorio:

```bash
bash install.sh
bash run-librerias.sh --segundos 60
```

Docker Compose monta [el esquema SQL](sql/001_tablas.sql) en el directorio de inicialización de PostgreSQL. En un volumen nuevo, PostgreSQL carga las seis tablas automáticamente. Con un volumen existente, `install.sh` comprueba las tablas, aplica el SQL si faltan las seis y se detiene si detecta un esquema parcial.

Consulte la [guía del Proyecto I](docs/proyecto-i/LEEME_ENTREGA.md) y las [decisiones del Proyecto II](docs/proyecto-ii-decisiones.md).
