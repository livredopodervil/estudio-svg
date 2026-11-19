# M1R-1a — Primeiro patch incremental da linguagem existente

Checkpoint: entrega experimental sem commit/push. Não cria DSL nem runtime paralelo.

## Alterações

- `web/title-gil.mjs`: novos títulos produzidos em formato vertical usam a resolução real e transformação `pixels/(height/8)` já usada pelo renderizador GIL; palavras longas demais geram erro em vez de desaparecerem silenciosamente. O texto ocupa zona superior, deixando a inferior para legendas. Fontes GIL pré-existentes continuam intactas.
- `web/title-gallery.mjs`: passa a dimensão real do projeto para novos títulos e títulos reeditados.
- `web/scene-objects.mjs`: amplia `motionSource` com 17 movimentos em programas GIL tipados para `media` (não introduz outro relógio nem tipos de objeto).
- `web/scene-object-editor.mjs`: disponibiliza os movimentos no inspector existente, em seção recolhível.

## Limites

- Esta etapa melhora novos títulos GIL e os movimentos dos objetos de mídia. NÃO remove automaticamente textos previamente desenhados nos SVGs, não reescreve a linguagem de roteiro inteira e não migra dados antigos.
- Foto/cena SVG de fundo legado só pode ser animada após conversão para objeto de mídia independente (ferramenta já existente).
- `stagger-in`/`stagger-out` são presets por objeto; escalonamento de listas (um ator por item ou grupos declarativos) entra na etapa M1R-2.
- Câmera 3D, rig, matrizes afins genéricas e constraints espaciais dependem de contratos com SpatialSeed e não são implementadas aqui.

## Teste Android

```
cd "$HOME/estudio_svg_v3_git" || exit 1
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh
```

Usar a URL e porta **efetivamente exibidas** pelo servidor. Recarregar em aba anônima. Abrir projeto 9:16 e inserir um título GIL novo, com preset de entrada/saída: confirmar legibilidade e ausência de colisão com legenda; títulos antigos não são alterados automaticamente. Converter imagem para objeto, selecionar e aplicar Ken Burns, Pan e Parallax no inspector; verificar seek para início, meio, fim e retorno a início. Exportar trecho curto e conferir a composição.

## Reversão

`python rd_studio_m1r1_aplicar.py rollback --repo "$PWD"` restaura apenas arquivos modificados se ainda estiverem exatamente iguais à versão aplicada, e remove arquivos novos desta etapa. Faz backup em diretório de metadados Git (compatível com worktree).

## Critérios de gate

`node --test tests/test_m1r_titles_motion.mjs` — falha bloqueia instalação. Suíte anterior e renderização visual real no Android permanecem necessárias antes de commit/push. Registrar SKIP separadamente.
