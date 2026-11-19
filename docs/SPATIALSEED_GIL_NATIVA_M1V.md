# M1V — SpatialSeed para GIL nativa (integração parcial)

Autor do projeto: Rogério Duarte. Assistência técnica: OpenAI.

## Contrato

- Importar `.spatialseed` ou JSON espacial pela ação de importação GIL existente, convertendo a fonte pela ferramenta real `RD_GIL_ROOT/tools/import_spatialseed.mjs` e pelo checkout configurado em `RD_SPATIALSEED_ROOT`.
- Não renderizar um MP4 intermediário. O programa convertido permanece em `gil_nativo.source`, compilado por `web/gil-native.mjs` na prévia e por `web/browser-render.mjs` na exportação web.
- Preservar o documento original em `gil_nativo.source_spatialseed` e verificar o SHA-256 na normalização do projeto. Nenhum `eval`/execução do documento como script.
- Conversão experimental/limitada aos recursos aceitos pelo conversor GIL já instalado. Não promete geometria arbitrária, PBR, colisões, físicas, materiais, áudio procedural genérico ou equivalência pixel a pixel com o viewer SpatialSeed.
- A exportação FFmpeg legada não é equivalente à exportação web GIL nativa; usar **Exportar vídeo no navegador** ou **Exportação em alta qualidade recuperável**, quando disponível e validada.
- Não há alteração do relógio: a duração nominal pertence à cena; animações GIL amostram o tempo absoluto do mesmo timeline existente.

## Verificação no Android

1. Confirmar `RD_GIL_ROOT` e `RD_SPATIALSEED_ROOT`, com `import_spatialseed.mjs` presente e checkout do SpatialSeed real no último caminho.
2. Iniciar o servidor: `RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" RD_SPATIALSEED_ROOT="<caminho-real-confirmado>" bash iniciar.sh`.
3. No navegador local `http://127.0.0.1:8771/`, selecionar um projeto de teste e uma cena; importar uma fonte `.spatialseed` pelo seletor GIL.
4. Conferir prévia ao mover timeline em `t=0`, meio e fim; salvar e reabrir; verificar persistência de `source_spatialseed` e `source` no JSON da cena; exportar pelo navegador e comparar quadros.
5. Confirmar que um documento inválido não altera o projeto; conferir vídeo legado, editor SVG, menus e áudio.

## Status

Patch preparado para prévia/revisão; não validado ainda no Termux Android. Não executar push, merge ou commit antes da inspeção visual. Publicação somente com autorização humana.
