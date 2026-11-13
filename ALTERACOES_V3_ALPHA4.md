# V3.0.0 Alpha 4 — timeline declarativa e manuais para LLM

**Status:** versão experimental, não integrada à `main`. A V2.7.4.1 permanece estável no commit `b6f3b3e`.

## Recursos implementados

- Motor compartilhado `timeline_easing.py` (sem GSAP) para animação 2D/SVG e cena espacial.
- Curvas `linear`, `suave`, `power1.*`, `power2.*`, `power3.inOut`, `sine.*`, `expo.out`, `back.out`, `bounce.out`.
- Faixas `repeticoes` (0–20), `yoyo` e escalonamento declarativo `alvos` + `intervalo` no SVG. Normalização expande grupos para, no máximo, 32 faixas por cena.
- Interface 2D: seleção de curvas, número de repetições e alternância de direção.
- Interface espacial: presets de pulsação e pulo, que utilizam o mesmo relógio da exportação.
- Três manuais em `docs/`: guia de geração JSON, prompt mestre e restrições de licença do GSAP. Exemplo de projeto em `examples/timeline_v3_alpha4.json`.
- Compatibilidade preservada para JSONs legados: `repeticoes=0`, `yoyo=false`, `easing=suave` por padrão.

## Não implementado / limites

- A biblioteca GSAP **não está incluída nem em execução**. Os nomes dos interpoladores não significam compatibilidade com sua API JS.
- Não há suporte aos plugins MotionPath, ScrollTrigger, MorphSVG, Flip, Draggable nem física.
- A captura e exportação MP4 usam o motor local Python/FFmpeg; fontes e codecs dependem do ambiente.
- Os controles em toque real no Android exigem validação do usuário antes de promover esta branch.

## Reversão

Antes de modificar o código após instalar, pode-se usar `git apply -R --check <patch>` seguido de `git apply -R <patch>`. Se houver commit dedicado, preferir `git revert` na branch candidata. Não executar `git reset --hard` e não mesclar na `main` nesta etapa.
