# M1R-2 — Inserção unificada, inspector após player, tipografia

## Escopo implementado
- Reutiliza os caminhos existentes para imagens, vídeos, catálogo SVG, título GIL, fontes GIL, áudio e criação de cena espacial. Não cria outro parser, player, compositor ou relógio.
- O diálogo de inserção não inicia automaticamente a mesma demonstração. Apresenta categorias, além dos exemplos GIL existentes; bibliotecas existentes permanecem autoridades.
- Inspector movido do espaço entre viewport e botões de execução para depois dos controles de reprodução; não bloqueia controles nem exige overlay; movimentos rápidos ficam à vista.
- Novos títulos escolhem composição por palavras por padrão para preservar kerning e ligaduras no texto SVG da palavra; modo letras legado continua editável, agora com medidas cumulativas que levam em conta pares de caracteres.
- Fonte GIL do título preserva o documento e o digest já gerenciado pela galeria. Não migra fontes antigas.

## Fontes e LaTeX
- A renderização da fonte GIL da base inspecionada usa SVG `<text>` e família `sans-serif` fixa. TTF/OTF/WOFF personalizados e seleção de fonte não estão integrados neste marco.
- Para suporte tipográfico completo, avaliar HarfBuzz.js ou fontkit/opentype.js; para texto 3D, troika-three-text com SpatialSeed. Não instalar bibliotecas ou fontes sem auditoria de licença.
- LaTeX **não estava integrado** nos arquivos auditados. `docs/ROTEIRO_04_CATALOGO.md` recomenda MathJax TeX→SVG; o catálogo o identifica como pendência, sem botão enganoso ou conversão automática.

## Execução no Android
`cd "$HOME/estudio_svg_v3_git" && RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh`
Abrir somente a URL/porta realmente anunciada pelo servidor (historicamente http://127.0.0.1:8771/).

## Verificação de aceitação
1. Abrir botão ＋ no viewport: mostrar categorias imagem, vídeo, SVG, título, GIL, fonte GIL, áudio, nova cena 3D.
2. Selecionar uma família SVG: reutilizar prévia/confirmacão da biblioteca; nenhum objeto novo por alteração de paleta.
3. Selecionar um clipe/imagem: importar na **cena atual**, preservando duração e narração.
4. Criar título `AVATAR` em modo palavras: medir kerning com fonte carregada, confirmar espaçamento natural e entrada suave; repetir no modo letras.
5. Selecionar objeto, abrir Propriedades: inspector deve aparecer após a barra do player, playback/seek imediatamente após viewport.
6. Aplicar Ken Burns e Pan; navegar para trás e frente na timeline e verificar seek determinístico.
7. Salvar/reabrir e exportar teste de 5s; fontes antigas e projetos em pastas não devem mudar.

## Limites
- A opção `+ 3D` cria nova cena, não importa um objeto SpatialSeed em cena SVG.
- Sem adaptador LaTeX nem gestão de fontes ainda. Não afirmar recursos ausentes como implementados.
- Nenhum commit/push automático.
