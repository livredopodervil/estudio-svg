# RD Suite — Motor único de animação SVG V3 (M1.5 experimental)

**Referência funcional:** Player V3 validado no Android. **Base Git:** Estúdio `6eaacb0`, SpatialSeed `c6996c5` (HUD-035). Patch exclusivamente no worktree experimental M1, sem mudar projetos salvos, branches de trabalho ou repositórios remotos.

## Contrato

`web_player/v3/runtime.js` é a fonte única do algoritmo de animação declarativa SVG: `ease`, `progress`, expansão de alvos, intervalos, `repeticoes`, `yoyo`, `pivo_x/y`, `data-pivot-x/y`, fulcro da linha (`x1,y1`), transformações e opacidade.

`createDOMAnimator(svg, animacoes).apply(progresso)` atende o Player V3 e a prévia do Estúdio sem iframe ou outro slider. `browser-render.mjs` solicita o SVG estrutural com `animation_engine:'v3'`, anima com `animateV3Markup()` e só então rasteriza diretamente nas dimensões solicitadas de vídeo (por exemplo, SVG intrínseco 1920×1080 para 1080p), sem ampliar raster de 1280×720. A exportação offline do navegador usa o mesmo `paintOffline`.

A exportação clássica Python/FFmpeg chama o mesmo runtime via processo Node persistente (`animation_bridge.cjs`), sem fórmulas Python paralelas nem fallback divergente. **Node.js é dependência do renderizador clássico de cenas animadas.**

### Pivôs

Prioridade: calibragem local do Player, `pivo_x/y`, `data-pivot-x/y`, extremidade inicial de `line` (`x1,y1`) e caixa geométrica quando obtida no DOM. Na exportação Python, paths/grupos sem informação geométrica suficiente e sem pivô explícito geram erro explícito, impedindo vídeos com pivô incorreto. As 11 repetições originais do besouro não são alteradas.

## Limites

A alteração consolida as **animações SVG declarativas**. GIL nativa, movimento de mídia e física SpatialSeed conservam seus próprios contratos e não são convertidos neste patch. `viewer.frame.capture` WebGL continua indisponível no runtime observado, portanto isto não corrige a exportação 3D em alta resolução.

## Aceitação no Android

- Prévia possui um slider, sem iframe, e mostra o besouro como o V3.
- Busca temporal para trás reproduz o mesmo quadro.
- Exportações por navegador e offline (720p/1080p) usam a mesma transformação SVG e proporção.
- Exportação Python/FFmpeg passa com Node.js presente ou falha explicitamente por falta de pivô.
- Player V3 mantém narração, calibração de pivô e controles existentes.
- O projeto `motion_spatial` editado não é substituído.

Sem commit/merge/push. Toda reversão verifica hashes antes de restaurar.
