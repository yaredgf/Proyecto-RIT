#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

compose=(
  docker compose
  -f docker-compose.yml
  -f compose.librerias.yml
)

if ! command -v docker >/dev/null 2>&1; then
  echo "No se encontró Docker."
  exit 1
fi

archivos=(
  docker-compose.yml
  compose.librerias.yml
  config/settingsCrawler.json
  config/semillas.txt
  IntegracionLibrerias/Dockerfile.final
  IntegracionLibrerias/requirements.txt
  IntegracionLibrerias/requirements-final.txt
  IntegracionLibrerias/scrapy.cfg
  IntegracionLibrerias/crawler_rit/settings.py
  IntegracionLibrerias/crawler_rit/database.py
  IntegracionLibrerias/crawler_rit/inicializar.py
  IntegracionLibrerias/crawler_rit/ciclo.py
  IntegracionLibrerias/crawler_rit/indice.py
  IntegracionLibrerias/crawler_rit/mantenimiento.py
  IntegracionLibrerias/crawler_rit/politicas.py
  IntegracionLibrerias/crawler_rit/spiders/semillas.py
  IntegracionLibrerias/crawler_rit/spiders/produccion.py
)

faltan=0

for archivo in "${archivos[@]}"; do
  if [[ ! -f "$archivo" ]]; then
    echo "Falta: $archivo"
    faltan=1
  fi
done

if [[ "$faltan" == 1 ]]; then
  echo "Coloque los archivos del complemento en las rutas indicadas."
  exit 1
fi

"${compose[@]}" config --quiet

mkdir -p \
  IntegracionLibrerias/datos \
  IntegracionLibrerias/logs \
  IntegracionPropia/datos

"${compose[@]}" up -d postgres

preparado=0

for intento in {1..30}; do
  if "${compose[@]}" exec -T postgres \
    pg_isready -U admin -d TheSearcher >/dev/null 2>&1; then
    preparado=1
    break
  fi

  sleep 1
done

if [[ "$preparado" != 1 ]]; then
  echo "PostgreSQL no quedó listo."
  exit 1
fi

cantidad=$(
  "${compose[@]}" exec -T postgres \
    psql -U admin -d TheSearcher -Atc \
    "SELECT count(*)
     FROM information_schema.tables
     WHERE table_schema = 'public'
       AND table_name IN (
         'sitios',
         'ciclos',
         'documentos',
         'versiones',
         'identificadores',
         'menciones'
       );"
)

if [[ "$cantidad" == 0 ]]; then
  if [[ ! -f sql/001_tablas.sql ]]; then
    echo "Falta sql/001_tablas.sql para crear las tablas."
    exit 1
  fi

  "${compose[@]}" exec -T postgres \
    psql -U admin -d TheSearcher -v ON_ERROR_STOP=1 \
    < sql/001_tablas.sql

elif [[ "$cantidad" != 6 ]]; then
  echo "El esquema está incompleto: se encontraron $cantidad de 6 tablas."
  echo "Revise el esquema antes de continuar."
  exit 1
fi

"${compose[@]}" build crawler_librerias

"${compose[@]}" run --rm --no-deps -T \
  crawler_librerias \
  python -c \
  "import crawler_rit.ciclo; import crawler_rit.spiders.produccion; print('Módulos nuevos disponibles.')"

"${compose[@]}" run --rm --no-deps -T \
  crawler_librerias \
  python -m crawler_rit.database

"${compose[@]}" run --rm --no-deps -T \
  crawler_librerias \
  python -m crawler_rit.inicializar

if [[ ! -f config/stopwords_en.txt ]]; then
  temporal=$(mktemp config/stopwords_en.XXXXXX)

  if "${compose[@]}" run --rm --no-deps -T \
    crawler_librerias \
    python -m crawler_rit.indice stopwords > "$temporal"; then

    mv -- "$temporal" config/stopwords_en.txt
  else
    rm -f -- "$temporal"
    echo "No se pudo generar el archivo de stopwords."
    exit 1
  fi
fi

echo "Instalación preparada."
echo "Prueba: bash run-librerias.sh --segundos 60"