#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")"
# M1h: disponibilizar runtime GIL ao Studio.
export RD_GIL_ROOT="${RD_GIL_ROOT:-$HOME/rd_studio_gil_v01/gil}"
for modulo in src/model.mjs src/timeline.mjs; do
  if [ ! -f "$RD_GIL_ROOT/$modulo" ]; then
    printf 'GIL ausente: %s\n' "$RD_GIL_ROOT/$modulo" >&2
    exit 1
  fi
done
exec python app.py servir --port 8771
