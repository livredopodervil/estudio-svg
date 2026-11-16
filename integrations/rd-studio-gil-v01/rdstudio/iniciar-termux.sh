#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
APP="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO="${1:-$HOME/rogerioduarte-studio-teste}"
if [ ! -d "$REPO" ]; then
  echo "ERRO: diretório não existe: $REPO" >&2
  echo "Execute primeiro: bash '$APP/preparar-worktree.sh'" >&2
  echo "Ou informe a cópia de teste: bash '$APP/iniciar-termux.sh' /caminho/do/site" >&2
  exit 1
fi
if [ ! -f "$REPO/index.html" ]; then
  echo "ERRO: o diretório não possui index.html: $REPO" >&2
  exit 1
fi
if command -v python3 >/dev/null 2>&1; then PYTHON=python3
elif command -v python >/dev/null 2>&1; then PYTHON=python
else echo 'Python ausente. Em Termux: pkg install python' >&2; exit 1
fi
exec "$PYTHON" "$APP/server.py" --repo "$REPO" --port "${RD_STUDIO_PORT:-8765}" --preview-port "${RD_STUDIO_PREVIEW_PORT:-8766}"
