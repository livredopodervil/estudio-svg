#!/usr/bin/env bash
# Creates a separate SITE worktree and stages only new player assets.
# Does not touch main, index.html, modules or SpatialSeed.
set -euo pipefail
if [[ $# -ne 4 || ( "$1" != '--check' && "$1" != '--apply' ) ]]; then
  echo 'Uso: bash instalar_no_site.sh --check|--apply /caminho/repo-site /caminho/pacote-publicado /caminho/worktree-nova' >&2
  exit 2
fi
MODE="$1"; SITE="$(realpath "$2")"; PKG="$(realpath "$3")"; TARGET="$4"
[[ -d "$SITE" && -d "$PKG" ]] || { echo 'Diretórios inexistentes' >&2; exit 1; }
[[ "$(git -C "$SITE" rev-parse --show-toplevel)" == "$SITE" ]] || { echo 'Forneça a raiz exata do repositório do site' >&2;exit 1; }
REMOTE="$(git -C "$SITE" remote get-url origin)"
case "$REMOTE" in
  git@github.com:livredopodervil/rogerioduarte.org.git|https://github.com/livredopodervil/rogerioduarte.org.git|https://github.com/livredopodervil/rogerioduarte.org) ;;
  *) echo "Origem do site não reconhecida: $REMOTE" >&2; exit 1;;
esac
[[ -f "$PKG/assets/estudio-player/estudio-player-v1.js" && -f "$PKG/apresentacoes/catalog.json" ]] || { echo 'Pacote web incompleto' >&2; exit 1; }
python3 "$(dirname "$0")/estudio_web_publish.py" verify --output-root "$PKG"
git -C "$SITE" show-ref --verify --quiet refs/remotes/origin/main || { echo 'origin/main não existe: atualize referências manualmente' >&2;exit 1; }
if git -C "$SITE" show-ref --verify --quiet refs/heads/feat/player-web-v1; then echo 'Branch feat/player-web-v1 já existe' >&2;exit 1;fi
if [[ -e "$TARGET" ]];then echo 'Worktree de destino já existe: nenhuma substituição' >&2;exit 1;fi
if [[ "$MODE" == '--check' ]];then echo 'PRÉ-VALIDAÇÃO OK: nenhuma alteração realizada';exit 0;fi
git -C "$SITE" worktree add -b feat/player-web-v1 "$TARGET" origin/main
[[ ! -e "$TARGET/assets/estudio-player" && ! -e "$TARGET/apresentacoes" ]] || { echo 'Destino contém caminhos de publicação: revisar antes de copiar' >&2;exit 1; }
mkdir -p "$TARGET/assets"
cp -R "$PKG/assets/estudio-player" "$TARGET/assets/"
cp -R "$PKG/apresentacoes" "$TARGET/"
git -C "$TARGET" add -- assets/estudio-player apresentacoes
git -C "$TARGET" diff --cached --check
echo 'SITE: staging preparado em branch feat/player-web-v1; sem commit/push/merge.'
git -C "$TARGET" status -sb
