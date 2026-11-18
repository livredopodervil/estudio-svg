# M1M — Correção de legendas + tempos de fala

**Estado:** patch local sobre M1L, sem commit/push. Branch experimental `feat/studio-interface-m1b`; HEAD Git previsto `fb3d580f7af03bb4aa9b88bbc435a4df2159956d`.

## Causa

O M1L criou `web/subtitle-frame.mjs` mas a allowlist de `app.py` não incluía a rota GET `/subtitle-frame.mjs`, produzindo HTTP 404 na importação dinâmica. Testes JS locais não exercitaram o servidor HTTP.

## Alterações

- Rota pública estritamente permitida para o módulo da própria aplicação.
- Edge-TTS gera MP3 e arquivo SRT com marcação `WordBoundary` em **uma chamada** via `--write-media` e `--write-subtitles`.
- A mesma chave de cache é mantida; o SRT fica em `cache/voices/<tts_key>.srt`, não versionado. Não há síntese automática adicional.
- Áudio → **Gerar voz e tempos Edge-TTS** permite refazer explicitamente locução e tempos na mesma chamada; até completar com sucesso, cache de áudio anterior é preservado.
- Áudio → **Carregar tempos da voz** importa o SRT já gerado para `cenas[].legendas.cues`; também é possível importar SRT/VTT/JSON externo.
- Tempos são relativos ao início da cena com `voice_delay` incluído. Quando cada cue é uma palavra, o tempo é exato conforme a marcação informada pelo Edge-TTS. Quando uma cue contém várias palavras, o intervalo é subdividido por estimativa.
- A exportação pelo **navegador** reutiliza o mesmo `subtitle-frame.mjs`; o render legado MP4 do Python ainda não incorpora legendas.
- Vozes já geradas sem SRT permanecem válidas; não inventar sincronismo exato a partir delas. Use geração explícita ou importação de arquivo.

## Validação Android

1. Reiniciar o processo Python do Studio para atualizar a allowlist.
2. Verificar `curl -I http://127.0.0.1:PORTA/subtitle-frame.mjs` **e** GET, preferencialmente `curl -fsS -o /dev/null -w '%{http_code}'`.
3. Recarregar a página em aba anônima para eliminar cache de scripts antigo.
4. Abrir Áudio → Legendas animadas e ativá-las. Clicar **Prévia das legendas**; avançar o seek.
5. Para tempos reais, primeiro gerar locução com **Gerar voz e tempos Edge-TTS**, confirmar nova síntese, depois conferir os cues no campo de tempos.
6. Importar um arquivo SRT/VTT local e verificar se funciona com uma locução importada.
7. Exportar pelo navegador e verificar a sincronização; sem afirmar que o MP4 legado tenha legendas.

## Limitações e segurança

- A leitura de SRT do cache só devolve as palavras da cena selecionada, derivadas da voz gerada localmente. Não serve arquivos arbitrários.
- A geração reusa o mecanismo de jobs com sua verificação de Origin já existente; nenhum endpoint novo de escrita direta é introduzido.
- O alinhamento emitido pelo serviço TTS pode não representar com precisão absoluta as pausas acústicas e varia por versão/voz.
- Cabeçalhos antigos e browsers cacheados exigem reiniciar servidor e atualizar página.
- Os achados M1j e testes `SKIP` seguem pendentes.
- Não remover arquivos não versionados nem fazer push antes do teste visual.
