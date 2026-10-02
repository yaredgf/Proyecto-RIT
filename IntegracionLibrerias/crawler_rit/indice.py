"""Índice TF-IDF local. Solo se deserializan índices propios y confiables."""
import argparse
import csv
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path
from uuid import uuid4

import joblib
from scipy.sparse import save_npz, load_npz
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS

from crawler_rit.database import conectar
from crawler_rit.settings import BASE_DIR, RIT_RUTAS, CONFIG_PATH

TOKEN = re.compile(r"(?i)\b(?:CVE-\d{4}-\d{4,}|CWE-\d+|CAPEC-\d+|[a-z0-9]+(?:[-_.][a-z0-9]+)*)\b")
CODIGO = re.compile(r"(?i)\b(?:CVE-\d{4}-\d{4,}|CWE-\d+|CAPEC-\d+)\b")

def tokens(texto):
    return TOKEN.findall(texto.lower())

def resolver(ruta):
    """Ruta de DB relativa al repositorio, no al directorio del contenedor."""
    relativa = Path(ruta)
    raiz = Path(os.getenv('RIT_REPOSITORY_ROOT', str(BASE_DIR.parent))).resolve()
    if relativa.is_absolute() or '..' in relativa.parts:
        raise ValueError(f'Ruta no admitida: {ruta}')
    # Compatibilidad con el volumen /app/datos ya utilizado.
    if relativa.parts and relativa.parts[0] == 'IntegracionLibrerias':
        destino = (BASE_DIR / Path(*relativa.parts[1:])).resolve()
        destino.relative_to(BASE_DIR.resolve())
    else:
        destino = (raiz / relativa).resolve()
        destino.relative_to(raiz)
    if not destino.is_file():
        raise FileNotFoundError(f'Archivo de la colección no accesible: {destino}. Monte también los datos del otro arañador si existen.')
    return destino

def vigentes():
    with conectar() as c:
        return c.execute('''
            SELECT DISTINCT ON (v.id_doc)
                v.id, v.id_doc, v.ruta_texto, d.url_normalizada AS url
            FROM versiones v JOIN documentos d ON d.id = v.id_doc
            WHERE d.estado = 'completada'
              AND d.tipo IN ('ficha', 'aviso_analisis')
            ORDER BY v.id_doc, v.fecha_descarga DESC, v.id DESC
        ''').fetchall()

def stopwords():
    ruta = CONFIG_PATH.parent / 'stopwords_en.txt'
    if ruta.exists():
        palabras = {x.strip().lower() for x in ruta.read_text(encoding='utf-8').splitlines() if x.strip() and not x.startswith('#')}
    else:
        palabras = set(ENGLISH_STOP_WORDS)
    palabras -= {'no', 'not', 'nor'}
    return sorted(palabras)

def documentos(filas, frecuencias):
    for fila in filas:
        texto = resolver(fila['ruta_texto']).read_text(encoding='utf-8')
        fila['fragmento'] = ' '.join(texto.split())[:300]
        frecuencias.update(tokens(texto))  # Incluye stopwords para estadísticas.
        yield texto

def construir():
    filas = vigentes()
    if not filas:
        raise RuntimeError('No hay versiones vigentes aceptadas para indexar.')
    raiz = Path(RIT_RUTAS['indice'])
    raiz.mkdir(parents=True, exist_ok=True)
    nombre = 'generacion_' + uuid4().hex
    temporal = raiz / (nombre + '.tmp')
    temporal.mkdir()
    frecuencias = Counter()
    try:
        vectorizador = TfidfVectorizer(tokenizer=tokens, token_pattern=None,
            lowercase=False, stop_words=stopwords(), norm='l2', dtype=__import__('numpy').float32)
        matriz = vectorizador.fit_transform(documentos(filas, frecuencias))
        save_npz(temporal / 'vectores.npz', matriz)
        joblib.dump(vectorizador, temporal / 'vectorizador.joblib')
        (temporal / 'documentos.json').write_text(json.dumps(filas, ensure_ascii=False), encoding='utf-8')
        total_bytes = sum(resolver(f['ruta_texto']).stat().st_size for f in filas)
        resumen = {'documentos_vigentes': len(filas), 'bytes_texto': total_bytes,
            'GB_decimales': total_bytes / 1_000_000_000,
            'palabras': sum(frecuencias.values()), 'palabras_distintas': len(frecuencias),
            'dimensiones_indice': list(matriz.shape)}
        (temporal / 'estadisticas.json').write_text(json.dumps(resumen, indent=2), encoding='utf-8')
        with (temporal / 'frecuencias.csv').open('w', encoding='utf-8', newline='') as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(['rango', 'termino', 'frecuencia'])
            for rango, (termino, frecuencia) in enumerate(frecuencias.most_common(), 1):
                escritor.writerow([rango, termino, frecuencia])
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib import pyplot as plt
        fig, ax = plt.subplots()
        valores = sorted(frecuencias.values(), reverse=True)
        ax.loglog(range(1, len(valores) + 1), valores)
        ax.set(xlabel='Rango', ylabel='Frecuencia', title='Frecuencia de palabras')
        fig.tight_layout()
        fig.savefig(temporal / 'frecuencias.png', dpi=160)
        plt.close(fig)
        destino = raiz / nombre
        temporal.rename(destino)
        puntero = raiz / 'actual.tmp'
        puntero.write_text(nombre, encoding='utf-8')
        os.replace(puntero, raiz / 'actual.txt')
        print(json.dumps(resumen, indent=2))
        return resumen
    except Exception:
        shutil.rmtree(temporal, ignore_errors=True)
        raise

def buscar(consulta, pagina=1):
    if pagina < 1:
        raise ValueError('La página debe ser mayor o igual a 1.')
    raiz = Path(RIT_RUTAS['indice'])
    generacion = (raiz / 'actual.txt').read_text(encoding='utf-8').strip()
    carpeta = raiz / generacion
    filas = json.loads((carpeta / 'documentos.json').read_text(encoding='utf-8'))
    codigos = sorted(set(x.upper() for x in CODIGO.findall(consulta)))
    permitidas = None
    if codigos:
        with conectar() as c:
            resultados = c.execute('''
                SELECT id_version FROM menciones
                WHERE codigo_identificador = ANY(%s)
                GROUP BY id_version
                HAVING COUNT(DISTINCT codigo_identificador) = %s
            ''', (codigos, len(codigos))).fetchall()
        permitidas = {r['id_version'] for r in resultados}
    resto = CODIGO.sub(' ', consulta).strip()
    resultados = []
    if not resto and codigos:
        resultados = [(f, None) for f in filas if f['id'] in permitidas]
        resultados.sort(key=lambda par: par[0]['id_doc'])
    elif resto:
        vectorizador = joblib.load(carpeta / 'vectorizador.joblib')
        matriz = load_npz(carpeta / 'vectores.npz')
        consulta_vector = vectorizador.transform([resto])
        # Producto de vectores L2 normalizados = similitud coseno.
        puntajes = (matriz @ consulta_vector.T).toarray().ravel()
        resultados = [(f, float(p)) for f, p in zip(filas, puntajes)
            if p > 0 and (permitidas is None or f['id'] in permitidas)]
        resultados.sort(key=lambda par: (-par[1], par[0]['id_doc']))
    resultados = resultados[:50]
    salida = []
    for fila, puntaje in resultados[(pagina-1)*10:pagina*10]:
        salida.append({**fila, 'similitud': puntaje})
    return {'total': len(resultados), 'pagina': pagina, 'resultados': salida}

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('accion', choices=['construir', 'buscar', 'stopwords'])
    p.add_argument('consulta', nargs='?', default='')
    p.add_argument('--pagina', type=int, default=1)
    args = p.parse_args()
    if args.accion == 'construir':
        construir()
    elif args.accion == 'stopwords':
        print('\n'.join(sorted(set(ENGLISH_STOP_WORDS) - {'no', 'not', 'nor'})))
    else:
        print(json.dumps(buscar(args.consulta, args.pagina), ensure_ascii=False, indent=2))
