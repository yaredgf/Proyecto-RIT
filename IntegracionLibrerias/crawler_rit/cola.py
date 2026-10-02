from pathlib import Path
from tempfile import NamedTemporaryFile
import os

from crawler_rit.database import conectar
from crawler_rit.settings import RIT_RUTAS


class ColaURLs:
    """Archivo de URLs pendientes administrado por el calendarizador."""

    def __init__(self):
        self.ruta = Path(RIT_RUTAS["cola"])
        self.ruta.parent.mkdir(parents=True, exist_ok=True)

    def leer(self):
        if not self.ruta.exists():
            return []

        lineas = self.ruta.read_text(encoding="utf-8").splitlines()

        # Eliminar líneas vacías y duplicados conservando el orden.
        return list(dict.fromkeys(
            linea.strip()
            for linea in lineas
            if linea.strip()
        ))

    def guardar(self, urls):
        """Reemplaza la cola mediante un archivo temporal."""
        urls = list(dict.fromkeys(urls))
        temporal = None

        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.ruta.parent,
                prefix="cola_",
                suffix=".tmp",
                delete=False,
            ) as archivo:
                temporal = Path(archivo.name)

                for url in urls:
                    archivo.write(url + "\n")

                archivo.flush()
                os.fsync(archivo.fileno())

            os.replace(temporal, self.ruta)

        finally:
            if temporal is not None and temporal.exists():
                temporal.unlink()

    def agregar(self, urls):
        self.guardar(self.leer() + list(urls))

    def quitar(self, url):
        self.guardar(
            pendiente
            for pendiente in self.leer()
            if pendiente != url
        )

    def sincronizar(self):
        """Reconcilia la cola con las URLs pendientes de PostgreSQL."""
        with conectar() as conexion:
            filas = conexion.execute(
                """
                SELECT url_normalizada
                FROM documentos
                WHERE estado = 'pendiente'
                ORDER BY fecha_descubrimiento, id
                """
            ).fetchall()

        pendientes = [fila["url_normalizada"] for fila in filas]
        permitidas = set(pendientes)

        # Conservar primero el orden de las URLs ya encoladas.
        existentes = [
            url for url in self.leer()
            if url in permitidas
        ]

        self.guardar(existentes + pendientes)
        return len(pendientes)


if __name__ == "__main__":
    cola = ColaURLs()
    cantidad = cola.sincronizar()

    print(f"Cola: {cola.ruta}")
    print(f"URLs pendientes: {cantidad}")