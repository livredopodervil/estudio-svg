#!/data/data/com.termux/files/usr/bin/bash
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$HERE"
for cmd in python ffmpeg ffprobe; do command -v "$cmd" >/dev/null || { echo "FALTA: $cmd"; exit 1; }; done
mkdir -p cache/{visual,audio,voices,poster,previews} midia modelos projetos render web/vendor
for OLD in "$HOME/estudio_svg_v25" "$HOME/estudio_svg_v24" "$HOME/estudio_svg_v23" "$HOME/estudio_svg_v22"; do
  if [ -d "$OLD/projetos" ]; then
    echo "Copiando projetos e mídias de $OLD sem substituir arquivos"
    python app.py migrar --origem "$OLD"
    for KIND in voices visual audio poster; do
      if [ -d "$OLD/cache/$KIND" ]; then
        for SRC in "$OLD/cache/$KIND/"*; do
          [ -f "$SRC" ] || continue
          NAME="${SRC##*/}"
          [ -e "cache/$KIND/$NAME" ] || ln -s "$SRC" "cache/$KIND/$NAME"
        done
      fi
    done
  fi
done
python app.py verificar
# Reutiliza a biblioteca avançada já instalada, sem alterar a V2.5.
if [ ! -e "$HERE/web/vendor/svgedit" ] && [ -d "$HOME/estudio_svg_v25/web/vendor/svgedit" ]; then
  ln -s "$HOME/estudio_svg_v25/web/vendor/svgedit" "$HERE/web/vendor/svgedit"
fi
printf '\nAteliê SVG V2.6: funciona offline, sem baixar biblioteca adicional.\n'
if [ -s "$HERE/web/vendor/svgedit/editor/Editor.js" ]; then
  echo 'SVG-Edit avançado disponível em /vetor-classico (uso opcional).'
fi
printf 'Inicie: cd "%s" && python app.py servir --port 8771\n' "$HERE"
