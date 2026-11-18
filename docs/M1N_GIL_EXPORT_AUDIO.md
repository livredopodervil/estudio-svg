# M1N — áudio procedural GIL na exportação pelo navegador

Checkpoint de desenvolvimento: branch `feat/studio-interface-m1b`, HEAD `fb3d580` (M1L/M1M não commitados).

## Causa e alteração

O exportador `web/browser-render.mjs` abortava a exportação ao detectar qualquer `compiled.cues`, embora a prévia aceitasse cenas GIL com `audio.tone`. O M1N suporta **somente** `resource ... audio.tone` constante ligado a `object` e `cue`, com `frequency`, `gain` e `wave` explícitos; usa os osciladores e envelopes do mesmo Web Audio e o **mesmo destino de mídia** do mix de narração/música. Não descarta cues. Outros tipos de som GIL continuam recusados com erro descritivo.

O relógio das cenas vem do mix de áudio. A fala pode estender a duração da cena, mas o GIL permanece associado ao intervalo nominal. Os objetos de mídia GIL respeitam `start`, `end`, `offset` e `loop` para seus sons. A síntese gera tons programados, não arquivos WAV adicionais nem voz.

## Testes realizados na preparação

- 6 testes independentes de parsing, recusa segura e agendamento de áudio Web Audio.
- 9 testes M1L/M1M de legendas e sincronismo.
- Projeto real de oito cenas (M1L) analisado: **16 cues `audio.tone`** distribuídos pelas duas cenas GIL.
- Sintaxe JavaScript de `browser-render.mjs` validada com `node --check`.

**Não houve exportação audiovisual real no Android neste ambiente.** O teste visual e auditivo no aparelho é obrigatório antes de commit/push.

## Inicialização mais recente no Android/Termux

```bash
cd "$HOME/estudio_svg_v3_git" || exit 1
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh
```

Porta confirmada pelo `iniciar.sh` no snapshot: 8771; confira também a saída efetiva do servidor.
Abrir no Chrome do **mesmo Android**: http://127.0.0.1:8771/

## Critérios de aceitação

1. Recarregar em aba anônima para descartar scripts antigos.
2. Abrir o projeto demonstrativo com 8 cenas e 2 fontes GIL.
3. Em Áudio, habilitar legendas e, quando necessário, gerar ou carregar tempos por palavra.
4. Usar **Exportar vídeo no navegador** (não o renderizador MP4 legado do Python).
5. Confirmar conclusão do arquivo exportado e reprodução de toda a duração.
6. Ouvir narração, música e **tons GIL** nas cenas 4 e 7; verificar ausência de duplicação, estalos e silêncio imprevisto.
7. Conferir legendas sincronizadas e dentro dos quadros em 16:9 e 9:16.
8. Salvar/reabrir o projeto; verificar console, catálogo e viewport sem regressão.

## Limitações

- Sons GIL diferentes de `audio.tone` exigem adaptador próprio e bloqueiam exportação: não são descartados silenciosamente.
- Não muda a prévia GIL, que ainda pode tratar os sons de forma diferente; apenas a exportação pelo navegador é alvo.
- O renderizador MP4 Python legado permanece fora do escopo.
- Validação por compilação e Web Audio simulado **não é** comprovação de MP4/WebM real nem de sincronismo perceptivo.
- Pendências de segurança M1j e testes `SKIP` seguem registradas; não tratá-las como resolvidas.

## Reversão

O instalador mantém backup em `.git/rdstudio-backups/m1n-*`. Executar `python ... rollback --repo "$HOME/estudio_svg_v3_git"` após conferir que nenhum arquivo M1N foi editado posteriormente. O rollback recusa sobrescrever mudanças divergentes. Não usa `git reset`, `git clean` ou push.
