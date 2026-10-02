"""Revisitas y retención. Ejecutar sin descargas ni indexación concurrentes."""
from pathlib import Path
from crawler_rit.database import conectar
from crawler_rit.settings import RIT_CONFIG, BASE_DIR
from crawler_rit.indice import resolver


def programar():
    docs = RIT_CONFIG['coleccion']['revision_documentos_meses']
    fichas = RIT_CONFIG['coleccion']['revision_fichas_meses']
    with conectar() as c:
        c.execute('''
            UPDATE documentos
            SET proxima_revision = ultima_revision +
                (CASE WHEN tipo = 'ficha' THEN %s ELSE %s END * INTERVAL '1 month')
            WHERE estado = 'completada' AND tipo <> 'listado'
              AND ultima_revision IS NOT NULL
        ''', (fichas, docs))
        r = c.execute('''
            UPDATE documentos SET estado = 'pendiente', intentos = 0,
                proximo_intento = NULL, ultimo_error = NULL
            WHERE estado = 'completada' AND
                (tipo = 'listado' OR proxima_revision <= CURRENT_TIMESTAMP)
        ''')
        print('Revisitas programadas:', r.rowcount)


def conservar(id_documento=None):
    limite = int(RIT_CONFIG['coleccion']['versiones_maximas'])
    if limite < 1:
        raise ValueError('Debe conservarse al menos una versión.')
    # Diario de borrado: si se interrumpe tras el commit, se reanuda después.
    import json, os
    diario = Path(BASE_DIR) / 'datos' / 'borrados_pendientes.json'
    diario.parent.mkdir(parents=True, exist_ok=True)
    pendientes = json.loads(diario.read_text()) if diario.exists() else []
    with conectar() as c:
        filas = c.execute('''
            SELECT id, ruta_html, ruta_texto FROM (
                SELECT v.*, ROW_NUMBER() OVER (
                    PARTITION BY id_doc ORDER BY fecha_descarga DESC, id DESC
                ) AS posicion FROM versiones v
                WHERE (CAST(%s AS BIGINT) IS NULL OR id_doc = %s)
            ) t WHERE posicion > %s
        ''', (id_documento, id_documento, limite)).fetchall()
        # Verificar el acceso antes de eliminar filas.
        for fila in filas:
            for campo in ('ruta_html', 'ruta_texto'):
                resolver(fila[campo])
        pendientes.extend(filas)
        tmp = diario.with_suffix('.tmp')
        tmp.write_text(json.dumps(pendientes), encoding='utf-8')
        os.replace(tmp, diario)
        if filas:
            c.execute('DELETE FROM versiones WHERE id = ANY(%s)', ([f['id'] for f in filas],))
    restantes = []
    for fila in pendientes:
        with conectar() as c:
            existe = c.execute('SELECT id FROM versiones WHERE id = %s', (fila['id'],)).fetchone()
        if existe:
            # La transacción anterior pudo revertirse; no borrar sus archivos.
            continue
        try:
            for campo in ('ruta_html', 'ruta_texto'):
                try:
                    resolver(fila[campo]).unlink()
                except FileNotFoundError:
                    pass
        except OSError:
            restantes.append(fila)
    tmp = diario.with_suffix('.tmp')
    tmp.write_text(json.dumps(restantes), encoding='utf-8')
    os.replace(tmp, diario)
    if restantes:
        raise RuntimeError('No se pudieron borrar algunos archivos; revisar permisos y repetir mantenimiento.')
    print('Versiones antiguas retiradas:', len(filas))

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('accion', choices=['programar', 'conservar'])
    a = p.parse_args()
    programar() if a.accion == 'programar' else conservar()
