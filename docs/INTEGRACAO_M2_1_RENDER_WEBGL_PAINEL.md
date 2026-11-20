# M2.1 — Integração de viewport, ferramentas e exportação WebGL (experimental)

Esta etapa modifica apenas o worktree `feat/studio-shared-scene-m2` do Estúdio. Não modifica o checkout SpatialSeed `main`, a Alpha 1 publicada ou o `main` do Estúdio. Autoria Estúdio SVG/RD Studio: Rogério Duarte. Créditos dos componentes permanecem inalterados.

## Implementado

- Um relógio lógico do Estúdio distribui `seek(t)` para adaptadores `spatialseed`, `svg` e `media` pela ponte M2. Não introduz outra engine ou outro relógio.
- Ferramentas SpatialSeed em painel flutuante externo ao `#stageShell`; no Android, o painel participa do fluxo da página e não cobre o vídeo. Espelha comandos e campos nativos do **mesmo iframe** SpatialSeed já carregado, encaminhando eventos para os elementos de origem. Não cria um segundo renderer.
- O exportador de vídeo **no navegador**, já existente, usa o stream do canvas SpatialSeed e compõe suas imagens com SVG, objetos GIL, mídias, legendas e mix de áudio no canvas final. Câmera por keyframes amostrada pelo tempo da cena.
- A exportação offline e a exportação servidor/HTML permanecem bloqueadas para WebGL. Essa proteção é deliberada.

## Limitações explícitas

- Captura real-time: sujeito a FPS perdido, visibilidade da página, desempenho WebGL no Android e suporte de `canvas.captureStream`/`MediaRecorder`. Não é renderização offline quadro-a-quadro determinística.
- O código do SpatialSeed não foi modificado; animações procedurais internas que não obedecem à timeline GIL ainda não têm busca por tempo absoluto. Os keyframes de câmera usam o tempo do Estúdio.
- Controles nativos simples e formulários são espelhados; diálogos avançados específicos do SpatialSeed ainda podem exigir a interface avançada original.
- Múltiplas trocas de documento `.spatialseed` durante uma mesma exportação podem exceder o tempo real e interromper com erro. Não há fallback silencioso para SVG/MP4 aproximado.
- O pacote foi testado com código-base e mocks, não com o SpatialSeed `main` real em Android. Aceitação visual e teste de exportação ainda são obrigatórios.

## Verificação

```bash
cd "$HOME/.local/share/rd-studio/worktrees/studio-shared-scene-m2" || exit 1
node --check web/studio-spatialseed-viewport.mjs
node --check web/studio-spatialseed-panel.mjs
node --check web/browser-render.mjs
node --check web/app.js
python -m py_compile app.py
node --test tests/test_studio_shared_scene.mjs tests/test_studio_spatialseed_panel.mjs tests/test_studio_m2_browser_export.mjs
```

Teste manual: iniciar o servidor na porta 8782 com os dois runtimes; abrir viewport WebGL, abrir ferramentas externas, editar objeto/câmera, criar dois keyframes e exportar vídeo pelo navegador com áudio e SVG. Verificar os primeiros e últimos quadros e comparar com a prévia. Nenhum push antes da aprovação.
