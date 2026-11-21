# AUD-U1 — RD-Audio: seletor unificado sobre motores existentes

Base: arquivos fornecidos em `rd_audio_base_real_20261119_182418.zip`; branch `feat/studio-shared-scene-m2`, HEAD `a47d2c8` com alterações locais M2.1–M2.4/M2.6/3.18 preservadas.

## Mudanças

- A aba Áudio passa a listar Piper e catálogo Edge no **mesmo seletor de personagem** (`rdRoleVoice`). A busca filtra por idioma e nome, mantendo vozes selecionadas.
- Não existe um segundo servidor ou editor. A API existente `/api/rd-voices/catalog` fornece os dados; o catálogo não é obtido da internet automaticamente.
- O orquestrador de narração `studio_audio_score.py` chama o adaptador `rd_voices/score_bridge.py` para Edge, que reutiliza `rd_voices.edge_engine.synthesize_edge`; Piper continua em `studio_piper_local.py` com compatibilidade mantida.
- Ritmo RD-Audio com `length_scale<1` acelera também Edge (`rate = round((1/length_scale - 1)*100)`), corrigindo o sinal anterior.
- Geração multivoz retorna `providers`; `motor_voz` só é atualizado automaticamente quando todos os personagens usam o mesmo provedor. Em roteiros mistos, mantém-se o motor global anterior e a mixagem gerada prevalece via `voice_file`.
- `@personagem b edge:pt-BR-AntonioNeural` e `@personagem c piper:faber` continuam com sintaxe original. As vozes Edge disponíveis dependem do catálogo real; o botão Vozes instaladas informa falhas.
- Browser speech não gera arquivo e Kokoro PT-BR permanece desabilitado. Nenhuma voz eSpeak é sintetizada por esta alteração.

## Validação

1. Verificar `python -m rd_voices info` e `GET /api/rd-voices/catalog` (se catálogo faltando, usar o fluxo de atualização Edge já existente, sem presumir disponibilidade da rede).
2. Abrir Estúdio no Android, aba Áudio; conferir opções Piper e Edge na mesma seleção, buscar `pt-BR`, inserir personagem e validar o roteiro.
3. Gerar uma fala Piper e uma Edge, ouvir no player da cena; salvar, fechar e reabrir; exportar áudio de cena SVG, conferir sincronismo.
4. Testar roteiro apenas Edge e misto, sem substituir o motor global por Piper indevidamente.
5. Executar `python -m unittest discover -s tests -p test_studio_audio_score.py -v`, `python -m unittest discover -s tests -p test_rd_audio_unified.py -v`, e `node --test tests/test_rd_audio_voice_picker.mjs`; SKIP não é PASS.
6. A exportação offline WebGL continua fora do escopo. Não publicar sem revisão visual e sonora.

## Reversão

O instalador fornecido registra os hashes de todos os arquivos alterados e de origem. Use `--revert` somente enquanto os arquivos ainda corresponderem à instalação; backups mantidos fora do worktree. Não executa `git reset`, `git clean`, `commit`, `push` nem altera `AGENTS.md`.
