#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
compose=(docker compose -f docker-compose.yml -f compose.librerias.yml)
command -v docker >/dev/null
"${compose[@]}" config --quiet
for archivo in config/settingsCrawler.json config/semillas.txt IntegracionLibrerias/requirements.txt; do
  test -f "$archivo" || { echo "Falta $archivo"; exit 1; }
done
mkdir -p IntegracionLibrerias/datos IntegracionLibrerias/logs IntegracionPropia/datos
"${compose[@]}" up -d postgres
preparado=0
for intento in {1..30}; do
  if "${compose[@]}" exec -T postgres pg_isready -U admin -d TheSearcher >/dev/null 2>&1; then
    preparado=1
    break
  fi
  sleep 1
done
if [[ "$preparado" != 1 ]]; then echo 'PostgreSQL no quedó listo.'; exit 1; fi
cantidad=$("${compose[@]}" exec -T postgres psql -U admin -d TheSearcher -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('sitios','ciclos','documentos','versiones','identificadores','menciones')")
if [[ "$cantidad" == 0 ]]; then
  test -f sql/001_tablas.sql || { echo 'Falta sql/001_tablas.sql'; exit 1; }
  "${compose[@]}" exec -T postgres psql -U admin -d TheSearcher -v ON_ERROR_STOP=1 < sql/001_tablas.sql
elif [[ "$cantidad" != 6 ]]; then
  echo 'El esquema está incompleto. No se ejecutará DDL sobre una instalación parcial.'
  exit 1
fi
"${compose[@]}" build crawler_librerias
"${compose[@]}" run --rm --no-deps crawler_librerias python -m crawler_rit.database
"${compose[@]}" run --rm --no-deps crawler_librerias python -m crawler_rit.inicializar
if [[ ! -f config/stopwords_en.txt ]]; then
  temporal=$(mktemp config/stopwords_en.XXXXXX)
  if "${compose[@]}" run --rm --no-deps -T crawler_librerias python -m crawler_rit.indice stopwords > "$temporal"; then
    mv -- "$temporal" config/stopwords_en.txt
  else
    rm -f -- "$temporal"
    exit 1
  fi
fi
echo 'Instalación preparada. No se inició una descarga masiva.'
echo 'Prueba: bash run-librerias.sh --segundos 60'
