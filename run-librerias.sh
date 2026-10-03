#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

docker compose config --quiet

docker compose run \
  --build \
  --rm \
  --no-deps \
  crawler_librerias \
  python -m crawler_rit.ciclo "$@"