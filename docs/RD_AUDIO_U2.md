# AUD-U2 — catálogo dinâmico de vozes no RD Studio (experimental)

Base: pacote `rd_audio_base_real_20261119_182418.zip`, branch `feat/studio-shared-scene-m2` HEAD `a47d2c8`; também aceita os arquivos gerados pelo AUD-U1 **somente** se seus hashes corresponderem. Não altera `AGENTS.md` nem outros arquivos; não faz Git commit/push.

## Contrato

`GET /api/rd-voices/installed` no servidor já existente retorna `voices` com `id`, `provider`, `voice_id`, `locale`, `available`, `exportable`, `online`. Cada voz possui identidade explícita `piper:cadu`, `edge:pt-BR-AntonioNeural`, `kokoro:pm_alex`, `espeak:pt-br`. Não há seleção silenciosa nem fallback entre motores. Browser voices aparecem como prévia apenas, não exportáveis por RD-Audio.

O painel Áudio original usa o mesmo seletor de personagens e insere a identidade na diretiva `@personagem`. Também permite `voz=...` na fala. A API já existente para `rd_voices` foi estendida; nenhuma porta nova. O mixer continua produzindo WAVs por cena e usando `voice_file`.

Piper: todos os modelos `*.onnx` com `.onnx.json` localizados em `~/piper_tts/`, com locale e taxa extraídos do JSON (Faber e Edresson legados permanecem reconhecidos). `pt_BR-cadu-medium` aparece como `piper:cadu` e `pt_BR-jeff-medium` como `piper:jeff`.

Edge: catálogo existente `rd_voices/catalogo_edge_20261119.json` ou cache atualizado via `python -m rd_voices refresh`; é possível selecionar qualquer idioma encontrado. Precisa de rede para síntese. Nenhuma rede é acessada automaticamente só por abrir o seletor.

Kokoro: nomes/indexação oficiais de `kokoro-multi-lang-v1_0` (`pf_dora=42`, `pm_alex=43`, `pm_santa=44`); só marca como utilizáveis vozes cujo léxico exista localmente em `~/kokoro_tts/kokoro-multi-lang-v1_0/`, com `espeak-ng-data`, Sherpa-ONNX e modelo. Português precisa do léxico `lexicon-pt.txt` (ou variante reconhecida). A presença dos arquivos não constitui teste auditivo. Síntese em subprocesso isolado, limite de 240s, PCM/WAV verificado, cache por modelo/voz/texto/velocidade. A relação `ritmo` em RD-Audio segue Piper (menor = mais rápido); o `speed` Kokoro é invertido ao sintetizar para preservar o significado.

O eSpeak-ng, quando executável, aparece como voz **legada opcional**: somente gera áudio por seleção explícita e nunca é fallback. Não constitui recomendação de qualidade. A biblioteca eSpeak usada internamente pelo Kokoro/Piper para fonemização não é uma voz sintetizada eSpeak.

## Limitações

Sem teste real Kokoro, Piper/Edge e interface no Android nesta entrega. A exportação WebGL continua pendente e não foi modificada. Não altera o Player V3, além de continuar usando o campo `voice_file`; a sincronização por palavras depende dos metadados Edge e de etapas posteriores.

## Testes

Antes de aplicar: `python instalar.py --repo <worktree>`.
Depois de aplicar: `python -m unittest discover -s tests -p 'test_audio_catalog_v2.py' -v`; `python -m unittest discover -s tests -p 'test_studio_audio_score.py' -v`; `node --test tests/test_rd_audio_all_voices.mjs`.
Abrir o Estúdio em `http://127.0.0.1:8783/` e, na aba Áudio, verificar Piper Faber/Cadu/Jeff/Edresson, Kokoro pt-BR (quando léxico presente), lista Edge em diversos idiomas, rotear duas vozes por personagens, gerar, ouvir, salvar e reabrir. Testar áudio no Player V3 e exportador. Não publicar sem validação humana.

## Reversão

O instalador imprime um comando `--revert` incluindo o caminho do backup externo. A reversão compara todos os hashes de saída e recusa sobrescrever alterações posteriores. Não executar `git reset` ou remover arquivos não relacionados.
