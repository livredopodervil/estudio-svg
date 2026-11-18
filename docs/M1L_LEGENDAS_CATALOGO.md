# M1L · Legendas animadas e catálogo de famílias

## Base

- Branch esperada `feat/studio-interface-m1b`, HEAD de referência `fb3d580f7af03bb4aa9b88bbc435a4df2159956d`.
- Patch incremental baseado no ZIP de fontes de 18/11/2026.
- Não altera a GIL externa, componentes existentes de cena, mídia, histórico Git nem o servidor de narração.

## Implementado nesta etapa

- `cenas[].legendas`: configuração persistida por `schema.py`; `enabled` é `false` por padrão nos projetos anteriores.
- Editor → Áudio: ativação, modos *karaokê/frase/palavra*, efeitos *subir/dissolver/ampliar/deslizar/digitar/nenhum*, posição, escala, cores, fundo e número de palavras.
- Prévia com a camada vetorial independente `rdSubtitleLayer`, que acompanha seek, pausa e tempo efetivo da cena.
- Exportação pelo navegador desenha as mesmas legendas diretamente no Canvas, depois de todas as demais camadas.
- Tempos explícitos opcionais `legendas.cues`: array de `{start,end,text}` em segundos desde o início da cena; persistem no JSON e têm prioridade sobre os tempos automáticos.
- `CATALOG_FAMILIES`: 24 geometrias, 1 tipo de texto e 18 famílias sonoras. Paletas, estilo, entrada e variante passaram a parâmetros do item. `CATALOG` legado foi preservado para compatibilidade.

## Limites reais

- **Tempos automáticos são estimados**, distribuídos por palavras segundo a duração efetiva da voz e atraso configurado. Não são alinhamento fonético nem eventos `WordBoundary` do Edge-TTS.
- `cues` explícitos permitem sincronização calibrada, mas ainda não são gerados automaticamente pelo motor TTS. A integração futura com `WordBoundary` exige modificar o contrato de síntese/backend e medir offsets reais.
- A exportação MP4 legada pelo Python/FFmpeg não recebe a camada de legendas. Use `Exportar vídeo no navegador` para composições GIL e legendas. Não afirmar equivalência com render legado.
- Presets de títulos GIL individuais continuam gerando camadas GIL (não objetos de texto editáveis por letra no inspector); a consolidação do inspector e da timeline é a próxima etapa.
- Os módulos no ZIP do diagnóstico são uma amostra e não incluem todo o servidor. Não introduzir API nova sem auditar `app.py` e testes.

## Teste Android/Termux

1. No repositório validado: `RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh`.
2. Ler porta e URL do servidor. Na configuração observada, `http://127.0.0.1:8771/`.
3. Abrir projeto com narração; aba Áudio → ativar legendas → selecionar *Karaokê* e *Subir e surgir*.
4. Testar `seek`, play/pause, a posição das palavras no viewport em retrato e paisagem, sem cobrir os quadros principais; trocar `Palavras por trecho` e o efeito.
5. Exportar pelo navegador com áudio e conferir os quadros e sincronização. A exportação precisa ficar em primeiro plano no Android.
6. Abrir `✧ Catálogo + Agente`: devem aparecer **43 famílias**, com paleta e efeitos como parâmetros, não centenas de variantes.
7. Navegar à `main` **somente se autorizado** e após backup; nesta etapa não fazer commit/push.

## Testes

- `node --test tests/test_m1l_subtitles.mjs`
- `python -m py_compile schema.py`
- `python tests/test_m1l_schema.py`
- `node --check web/app.js && node --check web/browser-render.mjs && node --check web/roteiro-v04-ui.mjs`
- `git diff --check`

## Reversão

Caso não haja outros patches sobrepostos, aplicar o patch reverso: `git apply -R --check <arquivo.patch>` e depois `git apply -R <arquivo.patch>`. Se houver alterações adicionais, comparar os hunks antes de reverter. Não usar `git reset --hard`.
