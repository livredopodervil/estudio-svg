# Captura e narração por cena — Estúdio SVG V3.5 experimental

Autor do projeto: Rogério Duarte. Esta alteração permanece na branch experimental.

## Operação
- Produção → Gerar voz desta cena: sintetiza apenas a cena selecionada usando o motor configurado. Quando já existe `voice_file`, exporta a gravação vinculada; para sintetizar texto, desvincule a gravação na aba Áudio.
- Produção → Estender cenas à narração: altera `encaixe_voz` para `estender` no projeto, sem reescrever as durações definidas; o renderizador ajusta o tempo necessário.
- Gravar narração: apresenta o roteiro, permite gravar/escutar/apagar trechos e unir os trechos em WAV PCM 16-bit. Um único trecho mantém o formato originalmente gravado pelo navegador.
- Perfis do microfone: Natural desativa AGC, supressão de ruído e eco; Tratada ativa essas opções. A disponibilidade depende do hardware, SO e navegador.
- Qualidade selecionável: valores solicitados ao `MediaRecorder`. O navegador pode utilizar outra taxa. Trechos múltiplos são convertidos a WAV, sem uma segunda compressão com perdas.
- Gravação de vídeo: preparar câmera é opcional e separado de Iniciar; abrir a janela não acessa câmera nem microfone.

## Limites e segurança
- A junção de trechos é feita em memória via Web Audio; limite de 160 MB PCM por captura. Para gravações longas use várias cenas.
- Não grava automaticamente; não transfere áudio para servidores externos; upload segue endpoint local original e exige confirmação.
- O texto editado no teleprompter não substitui `audio.voice_text` no projeto.
- Para gerar MP3 de uma única cena, o modo de backend `audio-cena` reutiliza a função `batch_audio` com uma lista de uma cena e o exportador `export_scene_voice`. A opção `export_zip=False` evita substituir `vozes_em_lote.zip` pelo resultado parcial; a exportação em lote permanece inalterada.
- A opção de ajuste `estender` não altera o arquivo JSON até o usuário salvar o projeto.
- Um `voice_file` já referenciado tem prioridade sobre a síntese; o botão de geração não sobrescreve áudio manual.

## Validação
`python -m unittest discover -s tests -p 'test_v35_capture.py' -v` e `node --check web/media-recorder-v35.js`. Teste manual no Android permanece necessário para qualidade do microfone, permissão da câmera, segundas tomadas e duração total.

## Reversão
`python instalar_captura_v35.py --repo CAMINHO --restore CAMINHO_BACKUP`; a restauração exige correspondência com hashes pós-patch.
