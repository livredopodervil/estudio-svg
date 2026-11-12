#!/data/data/com.termux/files/usr/bin/bash
# Instala o bundle pré-compilado oficial do SVG-Edit 7.4.2.
# Sem node/npm e sem compilar. Depois da instalação funciona offline.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
VERSION='7.4.2'
BASE="$HERE/web/vendor"
DEST="$BASE/svgedit"
if [ -s "$DEST/editor/Editor.js" ]; then
  echo "SVG-Edit já instalado em $DEST"
  exit 0
fi
command -v curl >/dev/null || { echo 'Instale: pkg install curl'; exit 1; }
command -v tar >/dev/null || { echo 'Instale: pkg install tar'; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
URL="https://registry.npmjs.org/svgedit/-/svgedit-${VERSION}.tgz"
echo "Baixando versão fixa do SVG-Edit ${VERSION} do registro npm oficial..."
curl --fail --location --retry 3 --connect-timeout 20 --max-time 240 "$URL" -o "$TMP/svgedit.tgz"
# Do not unpack a remote tarball blindly into the working directory.
# First check size and expected compiled assets, then extract into an isolated temporary folder.
test "$(wc -c < "$TMP/svgedit.tgz")" -lt 40000000 || { echo 'Arquivo excessivamente grande'; exit 1; }
tar -tzf "$TMP/svgedit.tgz" | grep -qx 'package/dist/editor/Editor.js' || {
  echo 'Esta versão npm não contém o bundle esperado: dist/editor/Editor.js'
  echo 'Instalação não efetuada. Nenhum arquivo existente foi modificado.'
  exit 1
}
mkdir -p "$TMP/unpack" "$BASE"
tar -xzf "$TMP/svgedit.tgz" -C "$TMP/unpack" --no-same-owner
# Keep sibling directories: the compiled editor may import from dist/svgcanvas etc.
test -s "$TMP/unpack/package/dist/editor/Editor.js" || exit 1
mkdir -p "$DEST.new"
cp -R "$TMP/unpack/package/dist/." "$DEST.new/"
# Preserve distributed license notices and package metadata.
cp "$TMP/unpack/package/package.json" "$DEST.new/PACKAGE_INFO.json" 2>/dev/null || true
for lic in LICENSE LICENSE.md LICENSE.txt; do
  if [ -f "$TMP/unpack/package/$lic" ]; then cp "$TMP/unpack/package/$lic" "$DEST.new/$lic"; fi
done
rm -rf "$DEST"
mv "$DEST.new" "$DEST"
echo "Instalado. Editor local: http://127.0.0.1:8770/vetor?name=demo_vetorial&scene=1"
echo 'No Estúdio, escolha o projeto demo_vetorial para testar as camadas.'
