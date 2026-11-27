#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

for config_file in config/dev.yaml config/test.yaml config/prod.yaml; do
  uv run python -c \
    'import sys; from src.utils.config_loader import load_config; load_config(sys.argv[1])' \
    "$config_file"
done
