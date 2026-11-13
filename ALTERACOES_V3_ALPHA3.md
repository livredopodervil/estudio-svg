# Estúdio SVG V3 Alpha 3 — importação e exportação independentes

- Importar ZIP contendo um único projeto JSON e mídias referenciadas (projetos/, midia/, assets/ ou raiz).
- Detecta traversal, symlinks, duplicações, mídia ausente, limites de tamanho e arquivos inválidos.
- Não sobrescreve: nomes de projeto e mídia ganham sufixos quando necessário.
- A locução importada **não** apaga o texto. Botões independentes removem gravação, música, faixas ou os vínculos de arquivos.
- O comando de remover arquivos de áudio não silencia a cena nem remove o roteiro. Para silêncio total, use a opção *Cena completamente silenciosa*.
- Exportar HTML autônomo com quadros SVG, imagens, vídeo convertido para H.264 e áudio MP3 embutidos em um arquivo (limite 145 MB). Há opção de HTML sem áudio com nome independente.
- A exportação de HTML utiliza a mesma função `graphics.visualize()` do renderizador, amostrada no `draw_fps` do projeto. Isso não é um navegador completo com edição interativa; é uma apresentação reproduzível offline.
- Para obter áudio no HTML, a exportação precisa preparar todas as narrações da mesma forma que a apresentação. TTS via internet pode necessitar conexão durante a **criação**, não durante a reprodução.
- Não substitui projetos antigos, não altera `main` e não faz commit nem push.
