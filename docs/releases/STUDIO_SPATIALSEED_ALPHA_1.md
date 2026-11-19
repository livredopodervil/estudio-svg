# RD Studio 3.14.0 — SpatialSeed WebGL Alpha 1

**Tag:** `studio-v3.14.0-spatialseed-alpha.1`

**Branch:** `experimental/studio-spatialseed-alpha-1`

**Base Studio:** `1cb222363ddc62f9096b06771c828081cd72f6e8`

**Dependência SpatialSeed:** `livredopodervil/SpatialSeed` branch `main`, commit `e50dc66f883ee1b3faad769457ad6ca6f819506c`.

**Autor do Estúdio:** Rogério Duarte. Dependências conservam seus créditos e licenças.

## Experimentação incluída

- Importação ZIP com mídias ausentes e vinculação posterior (M1 anterior).
- Ponte GIL nativa, camada SpatialSeed M1V/M1W (experimental).
- M1X: viewport SpatialSeed dentro da composição, câmera editável e keyframes vinculados
  ao tempo da timeline, com persistência no esquema.
- SpatialSeed permanece checkout independente, identificado por commit; atualização
  do motor não atualiza automaticamente documentos importados no Studio.

## Não disponível nesta versão

- MP4/HTML com WebGL: o exportador bloqueia explicitamente cenas SpatialSeed.
- Renderização quadro a quadro idêntica à prévia; eventos gerais entre WebGL, SVG e GIL.
- Sincronização automática de alterações externas `.spatialseed` ou projeção 3D→SVG.

## Validação de pré-publicação

Scripts de prévia e testes no worktree isolado. O release exige confirmação local
`--visual-ok` após verificação no navegador Android. O script de publicação
repete testes de regressão e não realiza push da `main`.

## Reversão

A branch estável `main` não é alterada. Para abandonar a alpha, retornar a um checkout
estável sem editar/apagar arquivos de trabalho, ou continuar com a versão anterior.
Não apagar históricos nem forçar atualização da tag.
