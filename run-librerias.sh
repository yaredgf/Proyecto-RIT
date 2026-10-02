#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

compose=(
  docker compose
  -f docker-compose.yml
  -f compose.librerias.yml
)

"${compose[@]}" config --quiet

"${compose[@]}" run \
  --build \
  --rm \
  --no-deps \
  crawler_librerias \
  python -m crawler_rit.ciclo "$@"