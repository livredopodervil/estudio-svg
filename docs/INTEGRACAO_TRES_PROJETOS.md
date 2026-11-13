# Estúdio Player Web v1 — integração de rogerioduarte.org, Estúdio SVG e SpatialSeed

**Estado:** implementação experimental isolada; não foi enviada ao GitHub.
**Autoria dos projetos:** Rogério Duarte. Respeitar créditos e licenças de terceiros.

## Objetivo e fronteiras

Este pacote tem duas responsabilidades: (1) converter projetos JSON do Estúdio em apresentações estáticas verificáveis; (2) exibi-las na web com narração opcional por `speechSynthesis`. O SpatialSeed permanece independente. Seus resultados visuais podem aparecer na publicação por meio da renderização SVG realizada previamente pelo Estúdio. **Não há integração do runtime interativo Three.js nem de scripts do SpatialSeed neste marco.**

A publicação evita inserir JavaScript proveniente do JSON ou do SVG no DOM da página. Os quadros são exibidos como `<img src="…svg">`, sem acesso ao estado do portal. O site existente (`index.html`, `js/site-v10.js`, `modules/manifest.json`, `modules/graph.js`) **não é alterado**. A primeira integração acontece apenas no subdiretório `apresentacoes/` e no módulo `assets/estudio-player/`.

## Fonte de verdade e sincronização

1. O projeto original JSON e suas mídias continuam no **Estúdio SVG**, que gera quadros SVG em tempo absoluto com `graphics.visualize`.
2. O publicador produz `apresentacoes/<slug>/manifest.json`, `frames/`, `assets/`, `media/`, `projeto.json` e `index.html`. `apresentacoes/catalog.json` agrega as publicações existentes.
3. O manifesto contém `source.projectSha256`, revisão Git do Estúdio, informação se havia mudanças rastreadas e, quando fornecido um checkout, commit do SpatialSeed. O script `verify` confere SHA-256 de cada recurso.
4. O repositório do **site** recebe os arquivos estáticos em uma *worktree* independente, na branch `feat/player-web-v1`. A integração visual nos dodecaedros/modificações em `modules/manifest.json` fica para um patch do site, após reconciliar o arquivo remoto atual. **Não duplicar relações no `modules/graph.js`.**
5. Não existe sincronização em tempo real entre repositórios neste marco: é uma **sincronização de publicação reprodutível**, com versões registradas e integridade verificável. A atualização de um projeto gera um novo slug/versionamento ou uma revisão controlada, nunca sobrescrita silenciosa.

## Instalação no repositório do Estúdio

Abra a V3 Alpha 4 em branch experimental, não na `main` estável. Extraia o ZIP de integração e execute:

```bash
cd "$HOME/storage/downloads/estudio_player_web_v1"
bash instalar_no_estudio.sh --check
bash instalar_no_estudio.sh --apply
```

O instalador exige `~/estudio_svg_v3_git` (ou `ESTUDIO_V3_ROOT` definido explicitamente), branch iniciada por `feat/v3` ou `release/v3`, remote SSH `livredopodervil/estudio-svg` e os módulos `graphics.py`, `schema.py`, `studio_core.py`. Adiciona exclusivamente arquivos novos. Não executa commit ou push.

## Gerar uma publicação

No diretório real do Estúdio, substitua `NOME` pelo nome existente do JSON, verificando antes `ls projetos`:

```bash
python tools/estudio_web_publish.py export \
  --project "projetos/NOME.json" \
  --media-dir midia \
  --slug nome-da-publicacao \
  --output-root "$HOME/estudio_player_stage"

python tools/estudio_web_publish.py verify \
  --output-root "$HOME/estudio_player_stage"
```

Opcionalmente, acrescentar `--spatial-dir /caminho/SpatialSeed` para registrar o commit espacial e `--require-clean` quando todas as alterações rastreadas estiverem commitadas. **Não habilite `--require-clean` antes de confirmar a V3 numa branch, porque esta versão foi desenvolvida como patch incremental.**

O programa não altera o JSON original nem os arquivos de mídia. Uma publicação existente não é substituída: utilize outro slug ou revisões versionadas (`sono-v2`). Clipes são convertidos a H.264 com FFmpeg, quando necessário. O player não publica áudio gravado automaticamente: prefere texto do JSON e a voz do navegador. Mídias referenciadas não encontradas interrompem o processo.

## Instalação no site, sem tocar na main

Confirme o caminho real do checkout local de `livredopodervil/rogerioduarte.org`, que possui CNAME `rogerioduarte.org`. Atualize previamente as referências remotas com `git fetch origin`. Não reutilize scripts antigos que substituam o site inteiro a partir de um ZIP.

```bash
bash tools/instalar_no_site.sh --check \
  /caminho/real/do/site \
  "$HOME/estudio_player_stage" \
  "$HOME/rogerioduarte_player_web_rc"

bash tools/instalar_no_site.sh --apply \
  /caminho/real/do/site \
  "$HOME/estudio_player_stage" \
  "$HOME/rogerioduarte_player_web_rc"
```

Apenas `assets/estudio-player/` e `apresentacoes/` são adicionados na nova worktree. O instalador interrompe se os destinos já existirem. Nenhum `index.html`, `modules/manifest.json`, script do site, CNAME, service worker, arquivo clínico ou mídia privada é modificado.

Testar a nova worktree com `python -m http.server 8800` e acessar a URL relativa de uma publicação. A publicação em GitHub depende da sua revisão de `git diff --cached --stat`, `git diff --cached --check` e dos testes visuais reais.

## Modos de incorporação

- **Página independente:** `https://rogerioduarte.org/apresentacoes/<slug>/` (após publicar a branch aprovada).
- **Seção de artigo:** exemplo em `site-examples/exemplo_embutido.html`, usando `<iframe loading="lazy">`. É a primeira opção recomendada porque isola o restante do site, inclusive o motor 3D.
- **Modal:** exemplo em `site-examples/exemplo_modal.html`, importando `openEstudioModal`. Fecha por botão, clique na máscara ou tecla Escape; interrompe narração e vídeo.
- **Elemento direto:** `<estudio-player src="/apresentacoes/<slug>/manifest.json"></estudio-player>` com import do módulo `assets/estudio-player/estudio-player-v1.js`.

## Narração e sincronização

O player lê `audio.voice_text` (normalizado pelo exportador como `voiceText`). A opção Voz inicia `SpeechSynthesisUtterance` após gesto do visitante. Prefere vozes `pt-BR` locais se fornecidas pelo navegador, mas nunca promete funcionamento offline. A cena tem duração mínima igual a `scene_length` sem voz; se o texto demorar mais, o player congela o último quadro até receber `onend`. Falha ou ausência de TTS ativa fallback visual com legendas. Não grava áudio, nem solicita microfone.

Vídeos da cena são reproduzidos **sem o áudio original** neste primeiro contrato, em camada sobre o SVG. A reprodução pode variar conforme codecs e política do navegador. A versão atual não replica a mixagem de música e efeitos nem faz exportação HTML autônoma de arquivo único: estas funções permanecem no Estúdio.

## SpatialSeed — ponto de integração

O SpatialSeed preserva `apps/web/build-info.json`, scripts e formatos `.spatialseed`. Não importar esses arquivos diretamente no player v1; isso exigiria um adaptador com sanitização, gestão de dependências, licença, estados persistentes e mapeamento de tempo absoluto. Para agora, o campo `source.spatialseed` registra o commit observado ou `null` quando o checkout não foi fornecido. `integration: pre-rendered-svg-only` sinaliza precisamente esse limite.

A futura Fase 2 poderá carregar uma cena 3D interativa em `iframe` isolado da aplicação SpatialSeed, **não** injetar seu runtime no portal. Um formato aberto de eventos e uma câmera controlada por tempo serão requisitos de interoperabilidade antes de qualquer integração de scripts.

## Auditoria e critérios de aceitação

```bash
python tools/auditar_integracao.py \
 --site /caminho/real/do/site \
 --studio /caminho/real/do/estudio \
 --spatial /caminho/real/do/SpatialSeed \
 --published "$HOME/estudio_player_stage"
```

O comando é somente leitura e emite JSON com remotes, branches, commits, estado de alterações rastreadas e validade dos recursos publicados. Os arquivos de publicação têm hashes SHA-256 verificados em disco. Não há Git push, pull, merge, checkout, reset ou edição de arquivos.

**Testes requeridos para promover:** código JavaScript sintaticamente válido, testes Python, prova de renderização de cenas com o renderizador real, importação de imagens e clipes, TTS no Chrome/Firefox/Android, retorno aos dodecaedros do site e nenhuma regressão em `verificar_integracao.py` do portal ou `tools/run_current_gates.py` do SpatialSeed.

**Reversão:** como a instalação é em novas worktrees e os arquivos são aditivos, descarte o commit candidato ou retire a referência à nova página. Nunca execute reset destrutivo sobre a `main`.
