# V2.7.4 — áudio exportável e posicionamento visual de vídeo

- Exportação independente da mixagem integral para MP3 160 kb/s ou Opus 96 kb/s.
- Exportação da narração de uma cena para MP3 160 kb/s, sem trilha de fundo.
- Gravação de áudio solicitando 160 kb/s com configurações opcionais de redução de eco/ruído.
- Captura de câmera em 720p (padrão) ou 1080p, com câmera traseira/frontal e bitrate sugerido ao navegador.
- Arrastar clipe sobre a prévia e redimensionar pela alça inferior direita.
- Preserve JSON existente; posição normalizada já suportada por `video_clipe`.

Limitações: o navegador e o dispositivo podem ignorar preferências de resolução e taxa de bits. A qualidade acústica depende também do microfone, ambiente e processamento do dispositivo. Testar com microfone/câmera reais no Android antes de integrar.
