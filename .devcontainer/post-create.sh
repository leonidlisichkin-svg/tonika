#!/usr/bin/env bash
# Runs once, when the dev container (the Codespace) is created.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  pipx install uv || python -m pip install --user uv
fi

# The project with its dev tools and the real Russian pack.
uv sync --extra ru

# Download the Russian models now (about 500 MB from Hugging Face), so the first real command
# answers at once. Not fatal: without them they download on first use.
if uv run tonika annotate --target plus "В старом замке сломался замок."; then
  echo "Tonika is ready."
else
  echo "The models were not downloaded now; they will download on first use."
fi
