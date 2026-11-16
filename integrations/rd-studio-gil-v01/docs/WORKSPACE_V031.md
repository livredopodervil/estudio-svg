# Workspace 0.3.1 / Estúdio SVG 3.9.1 experimental
Autoria principal: Rogério Duarte. Assistência: OpenAI.

## Janelas independentes
A barra do Workspace oferece Área inteira (fullscreen nativo do iframe) e Abrir separado (nova aba na origem do serviço). Salve ou baixe trabalhos antes de abrir outra instância: estado em memória não é compartilhado. Composição e vídeo oferecem ampliação da prévia. Apresentar / Gravar tela e Player Web V3 salvam o projeto e abrem uma nova aba; use Tela cheia com gesto explícito. No player, toque na área de vídeo para mostrar temporariamente controles de reprodução e saída. Android Voltar também pode sair de fullscreen. Nenhuma dependência ou alteração no SpatialSeed. Não usar exposição de rede.

## Som da prévia
Mix em cache é o relógio enquanto reproduz: a imagem segue currentTime; busca somente em navegação/resume e mudança de fonte. Voz isolada é fallback, com atraso e volume; espera limitada a cinco segundos na preparação ou interrupção; erro mantém a prévia visual. Redução de chamadas SVG para no máximo 10/s enquanto toca. A exportação mantém FPS do projeto. Áudio precisa estar salvo/gerado. Mudanças em memória continuam sem áudio até salvar. Na mudança de cena pode haver pausa de carregamento. Validar continuidade física no Chrome Android, também com clipes.

## Roteiro 0.1 — extensões compatíveis
- `corte A para B durante 0.04s`: opacidades A→0 e B→1 em paralelo; não troca documento ou câmera.
- `deslizar ID para [x,y,z] durante 1s`: smoothstep aproximado por cinco segmentos, a partir do estado anterior.
- `pulso ID para [sx,sy,sz] durante 1s`: vai à escala absoluta indicada na metade e retorna à escala anterior no fim.

Todas convertem em tracks GIL existentes, mantêm validação de propriedade, duração, faixa única, conflitos e IDs; limite de keyframes do modelo. As ações antigas mantêm interpolação linear. `gil/tools/visual_concepts/conceitos.py` contém primitivas de autoria, cartões, racks, fluxo de partículas, montagem, revelação, pulso e corte. `gerar.py --output NOVO_DIRETORIO` gera exemplo, sem sobrescrever. Na interface GIL: Programa GIL > Exemplo > Data center ou Roteiro de alto nível > Data center > Compilar > Enviar ao editor > Validar e aplicar. No Estúdio: Objetos / movimentos > exemplos GIL > Data center (clipe intermediário; não execução nativa). Escolha um trecho curto primeiro. Projeto de 36 s, 474 objetos, 316 faixas, 10 cues; locução escrita no metadado editorial, não sintetizada. Nenhum novo motor.

## Validação
`node --test gil/tests/*.test.mjs` no RD; `node --test tests/test_preview_transport_v391.mjs` no Estúdio. Suite recuperada da GIL: 55 passaram, 1 ignorado (dependência SpatialSeed externa); 5 testes de mídia simulados passaram. Compilação Python/JS verificável. Chromium de teste bloqueou acesso loopback pela política do ambiente; fullscreen e áudio real do Android não validados. Integração documental canônica e sincronização da locução por eventos permanecem próximas etapas.
