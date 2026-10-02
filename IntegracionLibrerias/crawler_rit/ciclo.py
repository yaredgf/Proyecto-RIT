"""Ejecuta una recopilación seguida por indexación. Una instancia a la vez."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

from crawler_rit.database import conectar
from crawler_rit.settings import RIT_RUTAS
from crawler_rit.inicializar import inicializar
from crawler_rit.mantenimiento import programar, conservar
from crawler_rit.indice import construir


def ejecutar(segundos=None, solo_indice=False):
    # La implementación propia debe usar la misma clave para exclusión mutua.
    with conectar() as bloqueo:
        fila = bloqueo.execute('SELECT pg_try_advisory_lock(43022026) AS obtenido').fetchone()
        if not fila['obtenido']:
            raise RuntimeError('Otra ejecución que usa el bloqueo del proyecto está activa.')
        try:
            if solo_indice:
                conservar()
                construir()
                return
            with conectar() as c:
                # Recuperar solo reservas del crawler con librerías.
                c.execute('''UPDATE documentos d SET estado = 'pendiente'
                    FROM ciclos c WHERE d.id_ciclo = c.id
                    AND c.implementacion = 'librerias' AND d.estado = 'en_proceso' ''')
                c.execute("UPDATE ciclos SET estado = 'interrumpido' WHERE implementacion = 'librerias' AND estado IN ('recopilando','indexando')")
                anterior = c.execute('SELECT COALESCE(MAX(id),0) AS id FROM ciclos').fetchone()['id']
            inicializar()
            programar()
            carpeta = Path(RIT_RUTAS['logs'])
            carpeta.mkdir(parents=True, exist_ok=True)
            nombre = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            comando = [sys.executable, '-m', 'scrapy', 'crawl', 'rit', '-s', f'LOG_FILE={carpeta / (nombre + ".log")}']
            if segundos is not None:
                comando += ['-a', f'duracion_prueba={segundos}']
            resultado = subprocess.run(comando)
            with conectar() as c:
                ciclo = c.execute("SELECT id FROM ciclos WHERE id > %s AND implementacion = 'librerias' ORDER BY id LIMIT 1", (anterior,)).fetchone()
            if resultado.returncode or not ciclo:
                raise RuntimeError('La recopilación terminó con error. Revisar el log; no se reemplazó el índice.')
            id_ciclo = ciclo['id']
            estadisticas = json.loads((carpeta / f'estadisticas_ciclo_{id_ciclo}.json').read_text())
            if estadisticas.get('rit/motivo_cierre') != 'finished' or any(
                clave.startswith('spider_exceptions/') and valor
                for clave, valor in estadisticas.items()
            ):
                raise RuntimeError('Cierre interrumpido o errores de programación: revisar el log antes de indexar.')
            try:
                with conectar() as c:
                    c.execute("UPDATE ciclos SET estado='indexando', inicio_indexacion=CURRENT_TIMESTAMP WHERE id=%s", (id_ciclo,))
                conservar()
                construir()
                with conectar() as c:
                    c.execute("UPDATE ciclos SET estado='completado', fin_indexacion=CURRENT_TIMESTAMP WHERE id=%s", (id_ciclo,))
            except Exception:
                with conectar() as c:
                    c.execute("UPDATE ciclos SET estado='fallido', fin_indexacion=CURRENT_TIMESTAMP WHERE id=%s", (id_ciclo,))
                raise
        finally:
            bloqueo.execute('SELECT pg_advisory_unlock(43022026)')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--segundos', type=int, help='Duración corta para prueba; omitir para usar JSON.')
    p.add_argument('--solo-indice', action='store_true')
    a = p.parse_args()
    if a.segundos is not None and a.segundos <= 0:
        p.error('--segundos debe ser positivo')
    ejecutar(a.segundos, a.solo_indice)
