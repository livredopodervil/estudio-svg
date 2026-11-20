# RD Studio — contrato de integração de todas as vozes (M2.5 experimental)

**Situação desta entrega:** SDK testável, catálogo de 318 vozes incluído e instalador aditivo. **Não há patch automático do editor real**, pois o checkout de M2/M2.4 não foi fornecido ao ambiente de construção. Os pontos de montagem devem ser confirmados com `AUDITORIA_RD_VOZES_318.md` e fontes reais. Não declarar a interface integrada até verificar no Android.

## Fonte de dados

O arquivo `todas_vozes_edge_tts.json` entregue em 19/11/2026 inclui 318 vozes em 142 localidades. Foi incorporado **integralmente** sob `rd_voices/catalogo_edge_20261119.json`, preservando `Name`, `ShortName`, `Gender`, `Locale`, `LocaleName`, `SuggestedCodec`, `FriendlyName`, `Status`, `VoiceTag` e todas as suas subchaves. Não foram substituídas as 3 vozes pt-BR nem eliminados outros idiomas.

A tela dispõe do botão **Atualizar vozes Edge**; `python -m rd_voices refresh` atualiza o catálogo local a partir da rede em `~/.cache/rd-studio/edge/catalogo_edge_latest.json`, sem sobrescrever o snapshot versionado. A lista e o total podem mudar conforme o serviço.

O código da biblioteca Python `edge-tts` só expõe `rate`, `pitch` e `volume` para variação direta de prosódia, além de nome de voz; não expõe `style` ou `styledegree` por conta da limitação SSML do serviço Edge. `VoiceTag.VoicePersonalities` são características **descritivas**, não emoções selecionáveis. Perfis `neutro`, `calmo`, `alegre`, `solene`, `tenso`, `triste` são **aproximações opcionais** aplicadas por parâmetros acústicos, NÃO emoções nativas. Não mandar tags Azure Speech `mstts:express-as` para `edge-tts`.

## Servidor do Estúdio — mesmo processo e porta

O módulo `rd_voices.api.try_handle(handler)` acrescenta rotas ao `BaseHTTPRequestHandler` **existente**, sem servidor secundário. Depois de inspecionar a classe do handler do repositório real, inserir no começo de seus `do_GET` e `do_POST`:

```python
from rd_voices.api import try_handle as rd_voices_route
if rd_voices_route(self):
    return
```

Se o servidor usar Flask, Starlette, FastAPI ou outro roteador, criar adaptador específico usando o mesmo `Catalog.load()` e `synthesize_edge()`; **não** colar o snippet `BaseHTTPRequestHandler` em framework incompatível.

Rotas do adaptador:
- `POST /api/rd-voices/refresh`: consulta rede para atualizar catálogo integral, mantendo o snapshot antigo em caso de falha.
- `GET /api/rd-voices/catalog`: catálogo normalizado com **todas as 318 vozes**, sem pré-filtrar idioma.
- `GET /api/rd-voices/controls.mjs` e `/controls.css`: componente único, para ser reutilizado nos painéis existentes.
- `POST /api/rd-voices/synthesize`: JSON `{text,voice:"edge:pt-BR-FranciscaNeural",prosody:{rate_pct:0,pitch_hz:0,volume_pct:0},intention:"neutro"}`. Gera áudio MP3 com palavras e cache.
- `GET /api/rd-voices/audio/<sha256>.mp3` e `/metadata/<sha256>.json`: saída do cache. A URL é local ao servidor.

Por segurança, a síntese só é aceita com `Host` local e `Origin` local (localhost ou 127.0.0.1). Caso se decida servir pelo IP de rede, alterar política de forma explícita após adicionar autenticação adequada.

## Frontend: UM controle reutilizado nas opções existentes

Incluir no HTML do editor original, sem criar outro painel/servidor:

```html
<link rel="stylesheet" href="/api/rd-voices/controls.css">
<script type="module">
import {mountVoicePicker} from '/api/rd-voices/controls.mjs';
// Adaptar os 3 seletores reais existentes de acordo com os identificadores do projeto:
await mountVoicePicker(document.querySelector('[data-role="scene-voice"]'), {
  scope:'scene', value: scene.voice,
  extraVoices: otherProviders, // mesmas vozes Piper/Kokoro que já estiverem validadas
  onChange: config => { scene.voice = config; persistProject(); }
});
await mountVoicePicker(document.querySelector('[data-role="character-voice"]'), {
  scope:'character', value: character.voice,
  extraVoices: otherProviders,
  onChange: config => { character.voice = config; persistProject(); }
});
await mountVoicePicker(document.querySelector('[data-role="script-voice"]'), {
  scope:'script-line', value: line.voice,
  extraVoices: otherProviders,
  onChange: config => { line.voice = config; persistProject(); }
});
</script>
```

Esses seletores são um **exemplo de contrato**, não IDs confirmados do repositório. O trabalho pendente é ligar `mountVoicePicker` aos callsites **reais** e evitar controles redundantes; a lista Edge, navegador e os demais provedores aparece no mesmo seletor do componente. O evento `rd-voice-change` facilita integração com o estado do editor. O callback `onPreviewOther` é fornecido pelo motor existente para Piper/Kokoro.

## Persistência e prioridade

Cada `scene`, `character` e `line` pode ter:

```json
{
  "voice": {"provider":"edge", "voice_id":"pt-BR-FranciscaNeural", "prosody":{"rate_pct":-8,"pitch_hz":-5,"volume_pct":0}, "intention":"calmo"}
}
```

Resolver prioridades por fala > cena > personagem > projeto, mantendo prosódia/intenções por nível. Use `resolve_voice_config()` do Python ou `resolveVoice()` no frontend (identidade). O esquema `make_voice_plan()` de referência é explícito; não substitui o manifesto existente sem migração validada. A seleção só é permanente quando o código existente de salvar/reabrir projeto persistir esses campos. **Não usar `localStorage` como substituto ao arquivo do projeto.**

## Vozes navegador, Edge, Piper e Kokoro

- Edge: MP3 no cache e tempos por palavra; usa rede. Sem substituição silenciosa em caso de falha.
- Navegador: vozes reais enumeradas via `speechSynthesis.getVoices()` no Android, com `rate`, `pitch`, `volume` **próprios da Web Speech API**. Não pressupor exportação do áudio.
- Piper: preservar `pt_BR-faber-medium` e `pt_BR-edresson-low`, se confirmados no aparelho; adaptador e parâmetros nativos continuam nos arquivos existentes do projeto. Não renomear voz legada como Edge.
- Kokoro: somente habilitar para síntese quando teste real confirmar texto PT-BR e áudio inteligível. Não cadastrar modelos não validados como vozes funcionais.
- eSpeak: não usar para narração.

## Execução por cena e exportação

Este SDK **não altera o player**. O adaptador de timeline deverá usar a URL e os `words` retornados para cada fala da cena; sincronizar com duração real do MP3 (`ffprobe`) e preservar o player geral, o modo `tocar cena`, pausa, seek e repetição. Falas do navegador em modo de prévia não garantem arquivo para MP4; ausência de exportação deve ser explícita. Não cortar fala no fim de cena. Código do player M2.4 é requisito para aplicar correção exata.

## Validação local

1. Rodar `python -m unittest discover -s tests -p 'test_rd_voices_318.py'` no repositório após instalação do SDK; e `node tests/test_rd_voices_ui_318.mjs` se Node instalado.
2. Confirmar catálogo com `python -m rd_voices info`, 318 vozes, 142 localidades; `python -m rd_voices list --locale pt-BR`, 3 vozes.
3. Instalar `edge-tts` no ambiente Python do Estúdio e gerar amostra com `python -m rd_voices speak --voice pt-BR-FranciscaNeural --text 'Teste de voz'`.
4. Verificar o mesmo seletor em cena, personagem, fala e narrador; checar que suas alterações sobrevivem a salvar/reabrir projeto.
5. Testar duas vozes pt-BR e uma voz não pt-BR, com prosódia neutra e modificada.
6. Tocar apenas cena 2 e depois roteiro inteiro; conferir áudio e transições no preview; testar export MP4 com fala até o fim.
7. Verificar que Piper, browser e projetos antigos seguem utilizáveis; classificar PASS, FAIL, SKIP sem tratá-los como equivalentes.
8. Antes de push, executar testes originais do Estúdio, aprovação visual Android e commits incrementais. Publicar apenas branch experimental com consentimento.

## Reversão

O instalador só cria arquivos novos em `rd_voices/`, `docs/RD_VOZES_318_INTEGRACAO.md` e `tests/test_rd_voices_318.py`, `tests/test_rd_voices_ui_318.mjs`; não adiciona nada ao Git nem altera rotas existentes. Verificar caminhos e hashes; remover **apenas os arquivos novos identificados pelo instalador**, caso se decida reverter. Qualquer patch posterior no servidor/editor terá diff e reversão próprios.
