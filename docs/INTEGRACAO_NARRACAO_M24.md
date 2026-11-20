# RD Studio M2.4 — Estúdio de Narração / RD-Audio 1

## Escopo implementado

- Painel de narração centralizado na aba **Áudio**; as configurações globais anteriores saíram da aba Projeto e foram mantidas em um bloco de compatibilidade na aba Áudio.
- Texto `audio_score` persistido no JSON do projeto, sem modificar formatos de cenas SVG/WebGL.
- Personagens com Piper Faber e Edresson, vozes e parâmetros por fala; controle de tempo absoluto local por cena.
- Emoções `neutro`, `calmo`, `alegre`, `triste`, `urgente`, `solene` são *orientações expressivas* mapeadas para ritmo e ganho; Piper **não recebe comandos semânticos de emoção**.
- Opções por fala `ritmo` (length_scale 0.70–1.30), `ganho` (amplitude 0–2), `pausa` (0–1 s). A fala inclui instruções de prosódia pela pontuação e segmentação textual.
- Efeitos de áudio previamente importados: `00:02.0 | !efeito | impacto.wav | ganho=0.5`. São mixados na faixa da locução da cena (não ficam editáveis em trilhas separadas).
- O compositor junta Piper + efeitos em um WAV mono 22.05 kHz por cena. `voice_file` mantém a mesma integração existente de prévia e exportação. `voice_delay` passa a 0 para preservar os marcadores absolutos.
- API com validação de roteiro sem síntese; disponibilidade do Piper e relatório Kokoro somente leitura.
- Cache por conteúdo, voz/modelo e parâmetros, sem modificar `~/piper_tts`, wrapper, glibc ou os modelos.

## Limitações e segurança

- **Kokoro não está habilitado para português**. O teste anterior produziu saída ininteligível. O detector não prova compatibilidade linguística; o projeto não seleciona Kokoro automaticamente nem gera sons ilegíveis.
- Piper Faber/Edresson não são *motores neurais emocionais*. Ganho/ritmo simulam dinâmica. Não há controle nativo de pitch, estilo emocional, clonagem de voz ou alinhamento fonético de palavras.
- O ritmo do roteiro é aplicado em cada segmento, não no áudio inteiro. Efeitos são somados e protegidos contra clipping pela atenuação geral quando necessário.
- O player de narração recebe uma mixagem por cena. A narração já gerada permanece vinculada enquanto `voice_file` existir; editar o roteiro requer gerar novamente para atualizar WAV.
- A duração da cena cresce apenas quando `encaixe_voz = estender`. Em outros modos, o editor mantém a duração original e exige conferência de possíveis cortes.
- Sem alterações no motor WebGL, codec de vídeo ou gravação de áudio. Falhas da renderização offline SpatialSeed continuam separadas desta versão.
- Exportações de legendas alinhadas por palavra da voz não são produzidas pelo Piper; o texto é preservado para as legendas e o usuário pode importar SRT/VTT.

## Sintaxe RD-Audio 1

```text
@personagem narrador faber
@personagem cientista edresson
@cena 1
00:00.0 | narrador | calmo | ritmo=0.94,ganho=1.0,pausa=0.2 | Texto a narrar.
00:03.5 | cientista | urgente | ritmo=0.90,ganho=1.1 | Outra fala.
00:05.0 | !efeito | impacto.wav | ganho=0.45
@cena 2
00:00.0 | narrador | neutro | ritmo=1.0 | Segunda cena.
```

`ritmo`: valor de `length_scale` (menor fala mais rápido); `ganho`: volume linear; `pausa`: silêncio entre sentenças. Tempo é relativo ao começo da cena. O resultado é armazenado no campo `audio.voice_file` e o roteiro original no campo de projeto `audio_score`.

## Verificar no Android

Servidor da branch experimental, com GIL/SpatialSeed externos já instalados:

```bash
cd "$HOME/.local/share/rd-studio/worktrees/studio-shared-scene-m2" || exit 1
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" \
RD_SPATIALSEED_ROOT="$HOME/.local/share/rd-studio/spatialseed-main" \
python app.py servir --port 8783
```

Em outra sessão:

```bash
termux-open-url "http://127.0.0.1:8783/"
```

Teste de aceitação: abrir **Áudio**; inserir dois personagens e duas cenas; **Validar roteiro**; **Gerar todas as cenas**; reproduzir no editor e Player V3; salvar e reabrir; ouvir ambas as vozes; conferir timing; exportar áudio/MP4 de uma cena SVG simples; alterar uma frase e gerar novamente. Não considerar os testes de WebGL offline cobertos por este patch.

## Compatibilidade e documentação

- Versão experimental: `M2.4 — RD-Audio 1` sobre o estado de arquivos gerado por M2.3; o instalador falha sem modificar o repositório se as verificações SHA-256 não forem satisfeitas.
- Não faz commit, push ou alteração da branch `main`. Documentar adoção e aceitação em `AGENTS.md` posteriormente, sem substituir o documento atual.
- Reversão restaura somente os arquivos que o pacote modificou, mediante verificação exata dos hashes instalados.

## Referências técnicas

- W3C SSML 1.1: https://www.w3.org/TR/speech-synthesis11/
- W3C EmotionML 1.0: https://www.w3.org/TR/emotionml/
- Piper CLI C++: https://github.com/rhasspy/piper/blob/master/src/cpp/main.cpp
- Kokoro Sherpa-ONNX: https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html
