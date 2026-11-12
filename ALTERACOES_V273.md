# V2.7.3 — Prancheta e mídia local

## Implementado

- A prancheta SVG passa a ter a mesma proporção do projeto. Ao abrir um SVG antigo em 9:16, o editor amplia o viewBox sem alterar as coordenadas dos objetos; a conversão só é salva após confirmação manual. O renderizador distingue SVG legado de SVG com altura integral.
- Controles para inspecionar animações: arraste a barra de 0 a 100% da cena, ou crie exemplo de entrada com fade/translação.
- Importação de um vídeo local por cena, em um quadro redimensionável definido por frações de x/y/largura/altura, com enquadramento cover/contain, início, repetição e opacidade. O vídeo é composto por FFmpeg acima do conteúdo SVG.
- Gravação local voluntária por microfone e câmera usando MediaRecorder, com prévia e aceitação antes de enviar ao servidor local. Áudio da câmera pode ser ligado à narração da mesma cena.
- Transferência em partes de arquivos de áudio e vídeo de até 250 MB. Verificação por FFprobe; os arquivos ficam em `midia/` (não rastreados).

## Limitações e riscos

- Vídeo de cena é uma camada **sobreposta**, não substitui o fundo nem fica entre objetos SVG. Som do vídeo só participa da mixagem se vinculado como `audio.voice_file`.
- `getUserMedia` e MediaRecorder dependem de navegador Android com suporte, permissões e acesso via localhost. Nenhuma mídia é enviada a serviços externos.
- Prévia HTML procura sincronizar o clipe com a linha do tempo; o MP4 final é produzido por FFmpeg. A validação física com câmera e microfone reais permanece pendente.
- Arquivos antigos permanecem compatíveis. Nenhuma migração ou sobrescrita automática de projetos antigos.
