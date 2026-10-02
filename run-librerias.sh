#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
docker compose -f docker-compose.yml -f compose.librerias.yml run --rm --no-deps crawler_librerias python -m crawler_rit.ciclo "$@"
