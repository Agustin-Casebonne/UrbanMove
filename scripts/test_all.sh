#!/bin/bash
# Ejecuta el linter y los tests de todos los microservicios (lo mismo que hace el CI).
# Uso desde la raíz del repo:  bash scripts/test_all.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== Lint"
ruff check .
ruff format --check .

for dir in services/*/; do
  name=$(basename "$dir")
  echo "== Tests $name"
  (cd "$dir" && PYTHONPATH="$ROOT/shared:." python -m pytest -q)
done
echo "== Todo OK"
