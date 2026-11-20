# Estúdio SVG / RD Studio — M2.6 | integração de voz (backend)

## Proveniência, limitações e base verificada

Patch criado com base no ZIP `fontes_studio_voz.zip` fornecido pelo usuário em 19/11/2026. O ZIP continha 101 entradas e um arquivo `MANIFEST_SHA256.json`, mas **não incluiu a árvore `web/`**, o repositório `.git`, dependências GIL/SpatialSeed nem todas as bibliotecas importadas. Consequentemente, a branch e o HEAD no Termux não foram inspecionados diretamente: o instalador valida branch e hashes dos arquivos afetados antes de escrever. Não modifica `main`, `AGENTS.md`, `web/`, modelos de voz, arquivos de projeto ou histórico Git. Não executa push.

A entrega **não conclui a montagem de seletores na interface do usuário**. O componente `rd_voices/controls.mjs`, presente no pacote recebido, ainda precisa ser montado nos formulários reais de roteiro, personagens, narração e cenas, cujos códigos HTML/JS não foram fornecidos. O backend inclui os dados e as rotas que esses seletores utilizarão. O player global e a execução por cena foram preservados sem modificação; teste da reprodução por cena no Android continua obrigatório.

## Arquivos alterados

- `app.py`: rotas já existentes do módulo `rd_voices` registradas no handler HTTP do Estúdio (GET/POST); as demais rotas permanecem inalteradas. Ajustes da exigência Edge por cena em geração de legendas.
- `schema.py`: persiste configuração opcional `voice` no projeto e em `cenas[].audio.voice`, sem mudar campos legados de voz (`voz`, `velocidade_voz`, `motor_voz`, `audio.voice_file`). Identidades explícitas de provedor e parâmetros validados.
- `studio_core.py`: seleção Edge/Piper por cena ou projeto para TTS, incluindo rate/pitch/volume Edge e assinatura separada de cache; fallback legado preservado **apenas** quando não houver nova seleção. Browser e Kokoro não são silenciosamente convertidos em vozes exportáveis.
- `studio_audio_score.py`: diretiva `@personagem` admite `edge:<ShortName>` com todos os 318 nomes do catálogo; `piper:faber`/`piper:edresson` e os nomes Piper legados continuam. Cada fala permite `voz=edge:<ShortName>` com parâmetros `ritmo`, `tom`, `volume`, `ganho`, `pausa`; sintetiza com Edge e usa o mixer WAV já existente. Browser/Kokoro podem ser registrados como intenção de prévia, mas o render do roteiro recusa explicitamente exportação sem motor suportado.
- `subtitle_times.py`: gera/recupera legendas da voz Edge escolhida por cena, mesmo quando a configuração global anterior não era Edge.
- `tests/test_rd_voice_m26.py`: testes de regressão.

## Prosódia e emoção

Edge TTS permite `rate` (%), `pitch` (Hz) e `volume` (%). Não oferece `style`, `styledegree` ou emoções nativas via biblioteca `edge-tts`. A coluna `VoiceTag.VoicePersonalities` é informativa. A coluna **emoção** do roteiro existente representa uma intenção dramatúrgica, realizada apenas por ritmo/ganho e mudanças acústicas aproximadas. Não gerar comandos Azure SSML `mstts:express-as` via Edge.

## Exemplo de roteiro (novo e retrocompatível)

```text
@personagem narrador edge:pt-BR-AntonioNeural
@personagem lucia edge:pt-BR-FranciscaNeural
@personagem tecnico piper:edresson
@cena 1
00:00 | narrador | neutro | ritmo=1.0,tom=0,volume=0 | Apresentamos o projeto.
00:03 | lucia | alegre | ritmo=1.1,tom=8,volume=4,ganho=1 | Bem-vindos.
@cena 2
00:00 | tecnico | calmo | ritmo=.95,pausa=.3 | Seguimos com a demonstração.
00:03 | lucia | neutro | voz=edge:pt-BR-ThalitaMultilingualNeural,tom=-4 | Outra voz na mesma personagem.
```

O parâmetro `voz` aplica-se somente à fala. Para parametrização por cena na narração simples, use JSON `cenas[i].audio.voice`; para parâmetros globais, use `voice` do projeto. A geração do roteiro retorna o WAV de cada cena, sem substituir automaticamente o arquivo de áudio do projeto até que o usuário o aplique por meio do fluxo existente.

```json
{
  "voice": {"provider":"edge","voice_id":"pt-BR-AntonioNeural","prosody":{"rate_pct":0,"pitch_hz":0,"volume_pct":0}},
  "cenas": [
    {"tipo":"globo","fala":"Teste", "audio": {"voice_text":"Teste","voice_enabled":true,
       "voice":{"provider":"edge","voice_id":"pt-BR-FranciscaNeural","prosody":{"rate_pct":-10,"pitch_hz":5,"volume_pct":0}}}}
  ]
}
```

## API na mesma origem

- `GET /api/rd-voices/catalog` lista **todas** as vozes Edge; não limita o idioma.
- `POST /api/rd-voices/synthesize` sintetiza MP3 Edge com prosódia e cache.
- `GET /api/rd-voices/controls.mjs` entrega o controle comum do módulo existente.
- `GET /api/rd-voices/controls.css` entrega o estilo comum.
- `POST /api/tts/score/validate` e `POST /api/tts/score/render` aceitam vozes Edge no roteiro.
- `POST /api/tts/piper` e recursos originais permanecem.

## Comandos após instalar no Termux

No terminal, verificar porta de teste M2 e comando real documentado em `README.md` do checkout. Se o aplicativo aceitar o comando de serviço presente na árvore completa, usar:

```bash
cd "$HOME/.local/share/rd-studio/worktrees/studio-shared-scene-m2" || exit 1
python -m unittest discover -s tests -p 'test_rd_voice_m26.py' -v
python -m rd_voices info
python app.py servir --port 8783
```

Outra sessão:

```bash
termux-open-url 'http://127.0.0.1:8783/'
```

Testar `curl -fsS http://127.0.0.1:8783/api/rd-voices/catalog` (ou usar Python para contar `voices`). Para Edge em uso real, instalar `edge-tts` na mesma instalação Python do servidor. A instalação não baixa nem sintetiza áudios automaticamente.

## Testes pendentes no Android

1. Confirmar 318 vozes na API ou o total atualizado na consulta ao serviço.
2. Ouvir uma voz Edge pt-BR e uma de outro idioma; conferir `rate`, `pitch`, `volume` no MP3.
3. Renderizar uma fala por personagem e uma com `voz=` por linha no roteiro.
4. Salvar/reabrir projeto e confirmar voz por projeto e por cena.
5. Testar pausa, seek, reprodução da cena isolada, troca de cena e player global.
6. Confirmar Piper existente e vozes browser intactas; browser não oferece arquivo de MP3 ao exportador.
7. Validar exportação MP4 de duas cenas com áudio completo e legendas.
8. Validar no Android em retrato e paisagem; não tratar testes não executados como PASS.

## Reversão

Executar `python instalar_m26.py --repo "$REPO" --out "$OUT" --rollback` somente após confirmar que os hashes de saída não mudaram. O programa reverte somente os cinco fontes afetados e remove seus próprios arquivos novos (`tests/test_rd_voice_m26.py` e este documento). Reversão é bloqueada se houver divergências no conteúdo desde a instalação.

## Próxima tarefa

Obter os arquivos reais do editor `web/index.html`, `web/app.js`, `web/style.css`, `web/roteiro-*.mjs`, `web/voice-bulk.mjs`, player e demais callsites da voz. Montar `mountVoicePicker` em todos os controles de seleção existentes, sem duplicar UI, e testar persistência pelo fluxo de salvar/reabrir. Não aplicar patch do frontend sem esses arquivos.
