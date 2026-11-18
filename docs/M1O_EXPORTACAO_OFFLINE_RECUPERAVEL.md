# Estúdio SVG — M1O: exportação determinística, alta resolução e retomada

**Estado:** patch experimental (não publicado), projetado sobre branch `feat/studio-interface-m1b`, HEAD `fb3d580f7af03bb4aa9b88bbc435a4df2159956d`, com M1L/M1M/M1N locais. Não é promoção a `main`. Preserva a exportação rápida antiga.

## Motivação / defeito observado

No projeto do arcabouço fiscal: 151,231604 segundos no contêiner MP4, 1.920 quadros realmente decodificáveis em H.264, apesar de 3.630 instantes programados a 24 FPS; taxa de imagem reportada por `ffprobe` `19200000/1503229` (aproximadamente 12,77 FPS). Alguns players exibiram cerca de 7 segundos. Não é prova de que o arquivo contenha apenas 7 segundos; exige exame de timestamps por faixa. O caminho atual avança com relógio de áudio + `requestAnimationFrame`; os passos desenhados podem ser pulados quando o aparelho está ocupado. `MediaRecorder` não fornece contagem de quadros codificados.

## Decisão M1O

O botão **Exportar sem perdas (recuperável)** usa o navegador apenas para construir cada quadro, sem `MediaRecorder` e sem relógio real; o tempo do quadro `n` é exatamente `t = n / fps`. `paintOffline` aguarda o PNG base, rasterização GIL e a tentativa de posicionar cada clipe no instante solicitado; as legendas são pintadas no mesmo canvas.

O servidor Python local recebe PNGs completos, verifica dimensões e sequência, salva cada quadro atomicamente e codifica blocos de até 48 quadros em MP4/H.264 com FFmpeg (`libx264`, CRF 16, `yuv420p`, sem B-frames). Os PNGs desse bloco só são removidos após segmentação concluída, validada com `ffprobe` e registrada em um manifesto durável. Crash no navegador ou servidor preserva blocos anteriores e PNGs incompletos do bloco atual; retomar o mesmo projeto, resolução, FPS e mídia reutiliza o checkpoint. Crash entre a escrita de um bloco e seu manifesto provoca reconstrução a partir dos PNGs originais.

Ao concluir, o servidor concatena segmentos em ordem, mistura o WAV do Studio com os efeitos `audio.tone` da GIL (gerados numericamente em PCM) e codifica AAC. O arquivo final é transferido atomicamente de `.partial.mp4` para `render/studio-offline-<id>.mp4` só depois que `ffprobe` confirmar exatamente a quantidade de quadros, frequência e duração do vídeo, uma faixa AAC e duração global coerente. `+faststart` aumenta a compatibilidade com players MP4. Nenhum arquivo de projeto ou arquivo de mídia existente é alterado. `main` e a branch remota permanecem intactas.

Os checkpoints ficam em `render/.offline-checkpoints/<token>/` e **não devem ser apagados durante uma renderização incompleta**. A limpeza é manual após validar o arquivo final. O servidor não consegue continuar renderizando sozinho após fechar a página; a **retomada** ocorre ao reabrir o Studio e selecionar novamente a exportação com a mesma configuração. O navegador deve permanecer aberto e operacional enquanto envia quadros, mas a renderização não precisa acompanhar o tempo real.

## Parâmetros

- `Resolução: Até 1920 px` aumenta proporcionalmente até 1920 pixels no maior lado. Presets 16:9 normalmente geram 1920×1080; verticais, 1080×1920. É ampliação de raster/vetores; uma foto ou vídeo de resolução inferior não ganha detalhes novos.
- `Resolução: Nativa do projeto` mantém o número de pixels de `video.width` e `video.height`.
- `video.fps`: 24, 25 ou 30 FPS, com todos os quadros enumerados e cronologia explícita. A opção `draw_fps` mais baixa do renderizador rápido não reduz o FPS GIL na renderização M1O.
- Encode H.264 CRF 16, perfil Main e `yuv420p`: alta qualidade perceptual e ampla compatibilidade, não compressão matematicamente sem perdas. PNGs temporários são sem perdas.
- Áudio: mix WAV gerado pelo servidor + eventos constantes `audio.tone` aceitos pelo M1N; outros tipos de som GIL são bloqueados explicitamente. Importações e voz do projeto dependem da mixagem existente no Studio.

## Limitações / riscos explícitos

- Para clipes importados, a busca temporal usa o elemento HTMLVideoElement e aguarda `seeked`. Há dependência do decodificador do navegador; exatidão de apresentação quadro a quadro para todos os codecs ainda requer testes específicos e eventualmente FFmpeg por clipe.
- Ao exportar um projeto muito pesado em 1920 px, o navegador consome CPU/memória na rasterização SVG e `toBlob` PNG. Isso pode demorar mais que a duração do vídeo. A persistência é segmentada para evitar depender de um único contêiner final.
- O fingerprint de retomada inclui projeto, configurações, vozes selecionadas e metadados dos arquivos de mídia referenciados. Se arquivos forem alterados, cria-se outra sessão, preservando as anteriores.
- Uma falta de espaço em disco, encerramento abrupto ou falha de FFmpeg mantém os arquivos já confirmados. Não considerar arquivo parcial como exportado.
- O servidor só atende em loopback; as APIs de escrita M1O exigem `Origin` e `Host` locais explícitos e um token aleatório, e limitam tamanho/formato de cada quadro.

## Gargalos do caminho anterior e instrumentação M1O

| Local | Causa | Tratamento M1O |
|---|---|---|
| `requestAnimationFrame` / relógio Web Audio | Pula instantes quando demora a desenhar; 1.681 passos perdidos observados | Índice de quadro explícito; nenhum passo omitido |
| `MediaRecorder` + `canvas.captureStream()` | FPS real de codificação depende do navegador; timestamps variáveis | FFmpeg offline por blocos com FPS constante e validação |
| `requestFrame` SVG/GIL | Rasterização assíncrona e reutilização de quadro anterior enquanto decodifica | `await` de cada SVG/GIL antes de gravar PNG |
| `POST /api/preview` e `svgImage.decode()` para muitos instantes | Overhead HTTP, parsing SVG e GC; provável custo importante | Ainda ocorre, mas é medido; otimização posterior requer detectar estaticidade segura e cache |
| `HTMLVideoElement.play()` para exportar em tempo real | Corrige deriva por seek, com custo e atraso | Busca explícita por instante, sem executar clipe em velocidade real |
| Grande WAV decodificado no Web Audio | Memória elevada, risco de suspensão do contexto | Mix e eventos GIL tratados no servidor e via PCM em blocos |
| PNG por quadro / HTTP sequencial (novo) | Custo de PNG, cópia e rede loopback | Limita memória, possibilita retomada; avaliar lote de quadros após medir |

O relatório do cliente acumula tempo de desenho, codificação PNG, upload e codificação de segmentos; o manifesto registra a duração real de FFmpeg por bloco e da finalização. Ainda não há medição de desempenho comparativo no Android, portanto **não declarar otimização de velocidade verificada**.

## Testes / aceitação

1. Antes do patch: confirmar branch, HEAD, backup e `git status --short`. Não remover alterações locais.
2. Aplicar instalador M1O; verificar resultados dos testes Python, Node e `git diff --check`.
3. Reiniciar servidor: `cd "$(git rev-parse --show-toplevel)" && RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh`. Usar somente a URL/porta **confirmada no terminal**; se `8771`, `http://127.0.0.1:8771/` no mesmo Android.
4. Abrir o projeto de 8 cenas; verificar áudio, legendas, GIL e duração efetiva (locução pode prolongar cenas).
5. Testar primeiro um trecho curto na resolução nativa, verificar botão novo. Interromper a exportação e iniciar novamente; a contagem deve começar do quadro salvo, não do zero.
6. Exportar o projeto inteiro em 1920 px; testar reprodução no Chrome/Android e em outro player. `ffprobe -count_frames` deve apresentar `nb_read_frames = ceil(duração * FPS)` e taxa constante igual ao FPS configurado. O arquivo final deve ter H.264 + AAC e duração igual a `quadros/FPS` com diferença inferior a ~0,12s.
7. Verificar legibilidade de subtítulos, quadros GIL e sincronia do áudio; medir tempos de desenho, PNG e FFmpeg. Não fazer commit/push até aprovação visual.

## Reversão

`python "$HOME/storage/downloads/rd_studio_m1o_aplicar.py" rollback --repo "$(git rev-parse --show-toplevel)"` restaura somente os arquivos M1O se os hashes finais ainda coincidirem e remove exclusivamente os novos arquivos M1O. Checkpoints/MP4 pessoais não são apagados. Sem `reset`, sem `clean`, sem commit/push automático.

## Diagnóstico de MP4 legado (sem recuperar animações que não foram desenhadas)

Para tentar corrigir a duração interpretada por players sem recomprimir vídeo, copie/remuxe com `ffmpeg -fflags +genpts -i ORIGINAL.mp4 -map 0 -c copy -movflags +faststart -avoid_negative_ts make_zero REPARADO.mp4`. Examine `ffprobe` depois. Se continuar incompatível, reencode com CFR a partir do arquivo existente, entendendo que isso **duplica** quadros para preencher a cadência e não recupera movimentos omitidos. Preserve o original e não sobrescreva arquivos.
