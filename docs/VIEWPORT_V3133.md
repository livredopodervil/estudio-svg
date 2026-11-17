# V3.13.3 — viewport unificado, apresentação e HTML independente

Autoria: Rogério Duarte. Base: V3.13.2 experimental; aplicação cirúrgica, sem alterações nas mídias ou projetos.

## Transformação
Uma única ferramenta `Transformar` permite selecionar pelo toque e arrastar o objeto para mover. Oito alças permitem escala não uniforme ou proporcional; alças dedicadas permitem rotacionar, cisalhar e deslocar o pivô. A ordem de camadas (↑ / ↓), inspeção e remoção ficam na mesma barra. A barra é parte do editor, posicionada via `position: fixed` com deslocamento limitado à janela do aplicativo, não ao quadro do vídeo; posição salva em `localStorage`. Ao entrar em fullscreen, é transferida ao elemento full screen.

## Apresentação
`/captura` carrega opcionalmente `gil-native.mjs` e `scene-objects.mjs` para apresentar objetos nativos em tempo real, em cima da cena SVG. O áudio de vídeo continua integrado ao mix existente. Gravação de tela usa `getDisplayMedia` e `MediaRecorder` apenas quando o navegador os suporta; no Chrome Android sem captura de tela, usar Exportar vídeo no navegador no editor. Não afirmar que áudio de dispositivo acompanha gravação sem verificação no aparelho.

## HTML autônomo
Quando o documento possui `gil_nativo` ou `objetos_midia`, `standalone_html.py` incorpora o programa GIL original e as referências de mídia de maneira autossuficiente: módulos JS permitidos do runtime configurado via `RD_GIL_ROOT` como `data:` modules em import map; vídeos e imagens como `data:` URL; mixagem se solicitada. Não cria vídeo intermediário de GIL. A gravação em HTML não está implementada; o HTML é um player independente. O caminho legado de HTML sem objetos nativos permanece.

Limites: template legado rasteriza as cenas base previamente; HTML continua limitado a 3600 amostras e 145 MB; clipes individuais têm limite de 120 MB. Arquivos HTML grandes podem esgotar memória móvel. WebGPU/WebGL não foram ativados; áudio de GIL cues ainda não é interpretado.

## Checklist Android
1. Manipulação no viewport: toque para selecionar; arraste a mídia para mover, cantos para escala, alças especiais para rotação/cisalhamento/pivô. Verifique que a mídia não é cortada.
2. Barra: arraste pela faixa ⠿ para fora do quadro, sem sair da tela. Teste modo foco, rotação e fullscreen. ↑/↓ devem mudar a ordem das camadas; ⚙ abre o inspetor.
3. Apresentar: iniciar reprodução de cena com GIL nativa, imagem e vídeo; conferir música/locução e sincronismo.
4. Gravar: testar o botão de captura de tela, se oferecido; no Android sem suporte, exportar pelo editor e conferir o arquivo baixado.
5. HTML autônomo: exportar projeto com GIL e imagem, abrir o HTML baixado sem servidor/internet; testar animação, mídia e som.
6. Regressão: salvar/reabrir projeto, desfazer/refazer e exportar 15–30 s com áudio. Não usar projeto único sem backup.
