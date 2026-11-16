# RD Studio / GIL 0.2.0 — autoria de componentes e render local

Autoria do sistema: Rogério Duarte. Assistência: OpenAI GPT. A DSL continua `gil timeline 0.1`, sem migração de projetos. O modelo, `PropertyRegistry`, `OccurrenceRef`, expressões e o runtime analítico existentes permanecem a autoridade do laboratório. Não é o sandbox nativo do SpatialSeed. Leia AGENTS.md e PROVENIENCIA.json; os módulos pinados não foram alterados.

## Autoria

Abra 8875 → Multimídia → GIL, ou 8791. Carregue Superposição de ondas. Em Hierarquia, selecione a linha para definir o objeto ativo; caixas marcam seleção para operações em lote (se vazio, usa ativo). Mesmo tipo seleciona todas as ocorrências daquele tipo, inclusive fora do filtro. À frente/atrás modifica `layer` base dos selecionados; não modifica descendentes implicitamente. Uma faixa animada pode sobrepor a propriedade base. Excluir remove subárvores e faixas/cues associadas, nunca arquivos de recursos. A câmera ativa é protegida. Duplicar subárvore reutiliza recursos, copia faixas/cues e gera novos IDs. Reorganizar mantém a transformação local, não a pose mundial.

Criar usa recurso existente ou declara um tipo arbitrário com propriedades escalares JSON (string, boolean, number); selecione Criar como filho quando desejado. O renderer só representa os tipos já suportados e diagnostica os demais. Isso não torna recursos arbitrários novos plugins executáveis. Para inserir keyframes, escolha propriedade numérica, clique na barra da timeline para escolher tempo, digite valor e insira. Faixas por expressão aceitam a linguagem afim já existente; uma faixa por par alvo/propriedade. Cues de audio.tone são eventos explicitamente posicionados. Undo/redo volta o documento inteiro em um passo, não a seleção. A fonte exportada após edição expande `repeat`: preserve o programa original se precisar da definição procedural.

## Comandos JSON compartilhados

O prefixo `edit` é extensão experimental do console GIL (não comanda o sandbox SpatialSeed). GUI e console usam `DocumentService.edit`, `planEdit` (puro), validação global e commit único.

```
edit {"op":"create","id":"sensor01","resource":{"id":"sensorCustom","kind":"arbitrary.sensor","props":{"value":0,"unit":"m/s"}}}
edit {"op":"track-put","id":"sensor01","property":"value","animation":{"expr":"2*sin(t)"}}
edit {"op":"set-many","ids":["sensor01"],"property":"value","value":3}
edit {"op":"duplicate","id":"sensor01","newId":"sensor02"}
edit {"op":"reparent","id":"sensor02","parent":null}
edit {"op":"track-remove","id":"sensor02","property":"value"}
edit {"op":"remove","ids":["sensor02"]}
undo
```

`cue-put` recebe id e timing `{start,duration}`; `index` opcional substitui um cue existente. `cue-remove` recebe id e index global atual. Use exclusivamente índices da revisão corrente. Não define métodos arbitrários, laços de eventos ou scripts JavaScript. Próximos contratos: revisão de planos, comandos canônicos de seleção, integrações de adapters WebGL e mixer de mídia.

## Exportação e página

`tools/launch.py` inicia `gil/tools/local_server.py` em loopback como serviço independente. O módulo não recebe token RD Studio, caminho de destino ou comandos de shell. Fonte aplicada + parâmetros validados → exportador existente → pasta temporária privada → HTTP vídeo com range e Content-Disposition. Apenas um resultado temporário por vez, máximo 1800 quadros, 120 s, 1280 px, 15 min; baixe antes de outra renderização ou de fechar o serviço. Não grava diretamente em Downloads; o navegador escolhe o destino. Primeiro teste 3 s, 12 FPS, 640 px. Se rasterizador ausente, verifique `command -v rsvg-convert` ou `python -c 'import cairosvg'` e ambiente; nenhuma instalação automática. Limites de arquivo RD Patch permanecem 8 MiB individual e 12 MiB total. Incluir na página verifica SHA-256 da fonte aplicada; a origem registrada em component.json distingue vídeo renderizado de vídeo anexado. O trecho pode ser menor que a composição (campo duration_requested). Não constitui prova criptográfica de autoria externa. Instalação/reversão continua no RD Studio. Nenhum post ou Git automático.

O servidor novo serve apenas HTML/JS/CSS e recursos permitidos, Host loopback exato, POST com Origin e token de sessão gerado no processo; sem CORS, sem acesso aos repositórios. Não o exponha em rede; não é sandbox para programas hostis. O exportador usa processos locais, não avalia JavaScript fornecido pela fonte. Ao reiniciar perdem-se os resultados temporários. Em servidor estático antigo o botão MP4 não funciona, mas player publicado é estático e não depende da API.

## Publicação

`python tools/publish_update.py --prepare "$HOME/estudio_svg_v3_git"` prepara atualização da branch de integração publicada em fde919dc. Confere a revisão e todos os hashes do manifesto anterior; somente arquivos alterados/novos do pacote e PACKAGE.json entram no worktree. Revise, teste, confirme direitos e execute o comando --publish impresso. Sem merge/reset/force. Não modifica branch V3.6 nem main do site. Para nova página: RD Patch original, em checkout atual e revisado do site, sem incluir data/social-latest.json. Bot YouTube continua independente. Não reutilize worktree de main desatualizado. `python tools/prepare_publication.py --prepare-demo CAMINHO_DO_CHECKOUT_GIT_DO_SITE` prepara agora apenas a página nova `projetos/gil-superposicao-ondas/` em worktree da main remota. Revise o diff e use --publish impresso. Não sobrescreve a demonstração cinética já publicada. O modo --prepare-source foi bloqueado nesta versão, substituído por publish_update.py.
