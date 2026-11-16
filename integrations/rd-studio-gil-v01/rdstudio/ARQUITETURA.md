# Arquitetura do RD Studio 4

- `server.py`: controle HTTP, sessão CSRF, editor de arquivos, vistas HTTP locais, Git e validação.
- `discovery.py`: inventário de aplicativos, comparador, geração de arte e portfólio 2D.
- `spatial.py`: grafo declarativo, posições dos módulos, dodecaedro de projetos, configuração espacial, assistente de publicação e restauração por snapshot.
- `web/spatial.js`: controles 2D de edição XY, campos X/Y/Z, gestão de arestas, editor paramétrico e assistente Git.
- `web/app.js`, `web/discover.js`: interfaces anteriores preservadas.

## Contratos do laboratório

`modules/manifest.json` é a única fonte das ligações 3D. Um módulo contém `id`, `name`, `menu` com 12 entradas, `position` `[x,y,z]` e opcionalmente `pages`, `texturePath` e `theme`. O dodecaedro `portfolio` é gerado a partir dos registros `catalog/projects/*.json`. As faces usam rotas completas de cada projeto, não serviços arbitrários.

`config/spatial.json` contém parâmetros limitados e validados: distância de câmera, zoom, velocidade de rotação, sensibilidade do arraste e autoplay. A adaptação do motor 3D é executada uma vez sob correspondência textual estrita e guarda backup automático. Atualizações posteriores são declarativas.

## Segurança Git

Somente branch `studio/`, origin GitHub autorizado, vistoria recente, SHA remoto e SHA local revalidados, sem rebase nem force push. Backups via tags imutáveis `site-pre-rdstudio-*`, associados ao commit remoto antes da publicação. Reversão via novo commit com restauração do snapshot em worktree limpo e alinhado.

## Atualização 4.2 — Controle direto da miniatura

O arquivo `aplicar-miniatura-sync.py` contém uma transformação auditável e verificável para o motor conhecido `js/site-v10.js`. O método `createMiniGraph()` utiliza `Pointer Events` com múltiplos IDs, atualização angular de estado compartilhado `miniPose`, aplicação instantânea das posições relativas em `arrange()` e cancelamento da transição de câmera durante gesto de pinça. O toque simples permanece seletor de módulos. Não altera outros projetos, registro de módulos ou estado Git. Os parâmetros de sensibilidade e zoom do adaptador RD Studio, se existentes, são reutilizados.


## Extensão 4.4: patches versionados

`patches.py` é um gerenciador declarativo isolado. Os endpoints são `/api/patches` (GET), `/api/patches/plan`, `/api/patches/apply`, `/api/patches/remove/plan` e `/api/patches/remove`. A mesma sessão local, token e verificação de Origin/Host do Studio original protegem operações de escrita. A aba `web/patches.js` não executa conteúdo do ZIP: apenas lista e solicita operações declaradas.

O pacote recebe `patch.json` com `schema=1`, `id`, `version`, `title` e `files`. Cada entrada tem `path`, `operation` add/replace, `sha256` e, para replace, `allowed_before_sha256`. O conteúdo está em `files/<path>` dentro do ZIP. Os caminhos são relativos à raiz do worktree. Arquivos não declarados, exceto README.md, são recusados.

Os backups ficam em `~/.rd-studio/pacotes/<hash-caminho>/ID/backups/`. O gerenciador não interage com Git, sendo possível revisar/publicar/remover seletivamente pelas ferramentas já existentes do Studio. Não reverte automaticamente commits ou backups remotos.


RD Studio 4.4.2: suporte a vídeo MP4 em pacotes RD Patch, limitado a 8 MiB por arquivo e validado por assinatura ftyp.
