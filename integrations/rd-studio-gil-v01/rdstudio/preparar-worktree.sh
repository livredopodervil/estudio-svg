#!/data/data/com.termux/files/usr/bin/bash
# Cria branch e worktree de teste a partir do GitHub, sem tocar no checkout publicado.
set -euo pipefail
SOURCE="${1:-$HOME/rogerioduarte-publicacao}"
TARGET="${2:-$HOME/rogerioduarte-studio-teste}"
if ! command -v git >/dev/null 2>&1; then
  echo 'Git não encontrado. Em Termux: pkg install git' >&2; exit 1
fi
if [ ! -d "$SOURCE" ] || ! git -C "$SOURCE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERRO: repositório de origem não encontrado: $SOURCE" >&2; exit 1
fi
if [ -e "$TARGET" ]; then
  echo "ERRO: destino já existe, sem sobrescrever: $TARGET" >&2; exit 1
fi
REMOTE="$(git -C "$SOURCE" remote get-url origin)"
case "$REMOTE" in *github.com*) ;; *)
  echo "ERRO: origin não parece ser GitHub; verifique o repositório: $REMOTE" >&2; exit 1;; esac
printf 'Origem: %s\nDestino independente: %s\n' "$SOURCE" "$TARGET"
echo 'Atualizando referências do GitHub (sem alterar arquivos locais)...'
git -C "$SOURCE" fetch origin main
git -C "$SOURCE" rev-parse --verify refs/remotes/origin/main >/dev/null
branch="studio/local-$(date +%Y%m%d-%H%M%S)"
git -C "$SOURCE" worktree add -b "$branch" "$TARGET" origin/main
printf '\nCriado. Branch: %s\nWorktree: %s\n' "$branch" "$TARGET"
echo 'Não houve commit ou push. Use iniciar-termux.sh para abrir o editor.'
