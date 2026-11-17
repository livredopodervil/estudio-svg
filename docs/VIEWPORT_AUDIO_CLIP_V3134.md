# V3.13.4 — Áudio, camadas legadas e animações GIL

Projeto: Estúdio SVG. Autoria: Rogério Duarte. Versão experimental.

## Contrato de reprodução

`web/media-start-gate.js` é o único controlador do início e interrupção de `HTMLMediaElement.play()` nos caminhos atualizados: editor, apresentação e HTML autônomo. A política de permissões/codec permanece do navegador. O ciclo de vida da mídia não deve confundir uma interrupção intencional com um bloqueio real. O HTML autônomo atribui o URI MP3 incorporado ao `<audio>`, operação que faltava no caminho antigo.

O player V3 preserva seu módulo de narração e não passa a ter um novo compilador GIL. Todos os objetos independentes continuam a usar `scene-objects.mjs`/`gil-native.mjs` no editor, apresentação e HTML autônomo. A arte SVG de base continua gerada pelo motor legado: **a convergência total dos renderizadores não está implementada**.

## Seleção de objetos existentes

Toque sobre clipe original abre a opção para convertê-lo explicitamente em objeto independente, preservando mídia, posição, tamanho, opacidade e áudio. A referência original é desativada em uma única edição reversível pelo histórico do documento. A transformação, estilos e programa GIL operam sobre a camada convertida. O SVG legado é selecionável para localizar suas opções existentes de desenho ou animação; a conversão automática de SVG para GIL está fora deste escopo.

## Estilo de mídia

Campos opcionais de objetos independentes:

- `corner_radius`: 0–0,5, fração do menor lado.
- `border_width`: 0–20 px.
- `border_color`: cor hexadecimal `#RRGGBB`.
- `shadow_blur`: 0–60 px.
- `shadow_color`: cor hexadecimal `#RRGGBB`.

Aplicação no DOM por `cssAppearance`, no Canvas por `canvasAppearance`. A aparência não invalida áudio em cache. O renderizador MP4 legado com FFmpeg não recebe esses novos efeitos; a exportação pelo navegador é a opção indicada para objetos independentes.

## Repertório de movimentos

Entrada com ampliação; saída com redução; fade de entrada/saída; entradas por direita, cima ou baixo; saída à esquerda ou direita; zoom de entrada/saída; rotação completa; flutuação; pulsação. Todas as animações são programas GIL sobre o grupo `media`, com keyframes e tempo local. A composição admite até oito programas adicionais, sem motor de animação paralelo.

## Limites e aceitação

O usuário deve verificar antes de integrar: áudio do HTML autônomo e página hospedada, sincronização de prévia, seleção de clipe/SVG legado, conversão e undo, manipulação, estilos, combinação de programas GIL, exportação em Canvas e download final. Testes no Chromium não substituem testes no Chrome Android. Nenhum commit/push automático desta atualização.
