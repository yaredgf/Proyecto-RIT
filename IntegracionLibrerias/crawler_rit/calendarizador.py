import time
from urllib.parse import urlsplit

from crawler_rit.cola import ColaURLs
from crawler_rit.database import conectar
from crawler_rit.settings import RIT_CONFIG


class Calendarizador:
    def __init__(self):
        self.cola = ColaURLs()
        self.id_ciclo = None
        self.inicio = None

        self.duracion = RIT_CONFIG["coleccion"]["duracion_segundos"]
        self.max_activas = RIT_CONFIG["descarga"]["concurrencia_total"]
        self.max_por_host = RIT_CONFIG["descarga"]["concurrencia_por_host"]

        # Reservas de esta ejecución: id_documento -> host.
        self.activas = {}

    def iniciar(self):
        """Registra un ciclo e inicia el tiempo de recopilación."""
        if self.id_ciclo is not None:
            raise RuntimeError("El calendarizador ya fue iniciado.")

        with conectar() as conexion:
            fila = conexion.execute(
                """
                INSERT INTO ciclos (
                    implementacion,
                    inicio_recopilacion,
                    estado
                )
                VALUES (
                    'librerias',
                    CURRENT_TIMESTAMP,
                    'recopilando'
                )
                RETURNING id
                """
            ).fetchone()

            self.id_ciclo = fila["id"]

        self.id_ciclo = fila["id"]
        self.inicio = time.monotonic()
        self.cola.sincronizar()

    def tiempo_agotado(self):
        if self.inicio is None:
            return False

        return time.monotonic() - self.inicio >= self.duracion

    def disponibles(self):
        """Consulta candidatas sin reservar ni cambiar estados."""
        candidatas = []

        with conectar() as conexion:
            for url in self.cola.leer():
                host = urlsplit(url).hostname

                fila = conexion.execute(
                    """
                    SELECT d.id, d.url_normalizada
                    FROM documentos AS d
                    WHERE d.url_normalizada = %s
                      AND d.estado = 'pendiente'
                      AND (
                          d.proximo_intento IS NULL
                          OR d.proximo_intento <= CURRENT_TIMESTAMP
                      )
                      AND EXISTS (
                          SELECT 1
                          FROM sitios AS s
                          WHERE s.host = %s
                            AND s.permitido = TRUE
                            AND (
                                s.proxima_solicitud_permitida IS NULL
                                OR s.proxima_solicitud_permitida
                                   <= CURRENT_TIMESTAMP
                            )
                      )
                    """,
                    (url, host),
                ).fetchone()

                if fila is not None:
                    candidatas.append({
                        "id": fila["id"],
                        "url": fila["url_normalizada"],
                        "host": host,
                    })

        return candidatas

    def reservar(self):
        """Reserva una candidata para esta ejecución."""
        if self.id_ciclo is None:
            raise RuntimeError("Debe iniciar el calendarizador.")

        if self.tiempo_agotado():
            return None

        if len(self.activas) >= self.max_activas:
            return None

        for candidata in self.disponibles():
            host = candidata["host"]

            activas_host = sum(
                valor == host
                for valor in self.activas.values()
            )

            if activas_host >= self.max_por_host:
                continue

            with conectar() as conexion:
                # La condición evita reservar una URL que otra
                # ejecución ya tomó después de nuestra consulta.
                fila = conexion.execute(
                    """
                    UPDATE documentos
                    SET estado = 'en_proceso',
                        id_ciclo = %s,
                        intentos = intentos + 1
                    WHERE id = %s
                      AND estado = 'pendiente'
                      AND intentos < %s
                      AND (
                          proximo_intento IS NULL
                          OR proximo_intento <= CURRENT_TIMESTAMP
                      )
                    RETURNING id
                    """,
                    (
                        self.id_ciclo,
                        candidata["id"],
                        RIT_CONFIG["descarga"]["intentos_totales"],
                    ),
                ).fetchone()

            if fila is None:
                continue

            self.activas[candidata["id"]] = host
            self.cola.quitar(candidata["url"])

            return candidata

        return None

    def liberar(self, id_documento):
        """
        Libera el cupo después de registrar en PostgreSQL
        el resultado de la tarea.
        """
        self.activas.pop(id_documento, None)


def mostrar_disponibles():
    calendarizador = Calendarizador()
    candidatas = calendarizador.disponibles()

    print(f"URLs disponibles ahora: {len(candidatas)}")

    for candidata in candidatas:
        print(f"{candidata['id']}: {candidata['url']}")


if __name__ == "__main__":
    mostrar_disponibles()