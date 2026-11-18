# Estúdio SVG — contrato de desenvolvimento

Autor: Rogério Duarte. Respeite licenças e créditos das dependências.

- Antes de alterar, confirme repositório, branch, HEAD, diff, testes e ambiente.
- `main` é a base canônica; trabalhe em branch/worktree isolado. Nunca sobrescreva arquivos locais de projeto, mídia, cache, backup ou credenciais.
- Modifique somente o necessário. Preserve o Ateliê SVG, suas camadas, undo/redo, salvamento e renderização existente.
- Use um dedo para edição e dois dedos para navegação na prancheta; gestos não alteram o SVG serializado.
- Teste compatibilidade dos JSONs antigos e novos, renderizador SVG e formatos 16:9 e 9:16.
- Valide no navegador mobile e, antes da integração, no Android/Termux real.
- Reporte objetivamente testes executados, hipóteses, limitações e rollback.
- Não faça push, merge, reset destrutivo nem publicação sem autorização.
- Conserve os módulos externos em `web/vendor/` fora do controle de versão até auditoria explícita de licenças.

- Na V2.7.2, animações são determinísticas e devem produzir os mesmos estados SVG na prévia e no MP4; nenhuma interpolação deve depender de timers do navegador.
- Música global contínua é opção explícita e deve preservar os arquivos de áudio e o comportamento dos JSONs antigos.

## V2.7.3 — Regra de mídia e enquadramento

- A prancheta SVG deve ter a mesma proporção do vídeo final. Arte legada 1280 × 720 é adaptada sem mudanças de coordenadas e somente salva após aprovação explícita. Prévia e MP4 devem receber exatamente o mesmo SVG e dimensões.
- Gravações de microfone e câmera exigem gesto de usuário e permissões locais; nunca iniciar silenciosamente, nunca fazer upload remoto. Arquivos ficam em `midia/`, ignorados pelo Git.
- Videoclipes são camadas sobrepostas, sem áudio por padrão; o som precisa estar explicitamente vinculado à narração da cena. Evitar modificações no pipeline de música contínua.
- Validar o `video_clipe` em JSON, a extensão/codec do arquivo por FFprobe e o MP4 com FFmpeg; preservar a edição SVG, os projetos antigos e os testes anteriores.

## V3 experimental · separação da versão estável

- A versão estável publicada permanece na `main` (`b6f3b3e`, V2.7.4.1). Não integrar `feat/v3-espacial-alpha` nem publicar alterações sem aprovação do usuário.
- A V3 usa `spatial_scene.py` como contrato mínimo; o código do SpatialSeed **não foi copiado**. Antes de incorporar componentes reais, verificar origem, versão fixa, dependências e licenças, preservando créditos.
- Cenas `espacial` são opcionais. Todo código de importação, normalização, prévia, exportação e testes deve manter os tipos legados sem regressão.
- Script de LLM = operações tipadas validadas, sem `eval`, execução arbitrária, redes ou escrita de arquivos.
- Renderização temporal deve depender exclusivamente do projeto e do instante, não do FPS ou estado mutável acumulado.

## V3 Alpha 4 — timeline e licenças

- `timeline_easing.py` concentra as curvas, ciclos finitos e yoyo usados pela animação SVG e espacial. Não bifurcar relógios/interpoladores entre prévia e exportação.
- `alvos` e `intervalo` são expandidos por `schema.animation_dict`; a cena persistida deve ser normalizada e limitada a 32 faixas.
- GSAP não está integrado. Revisar `docs/LICENCAS_GSAP.md` antes de redistribuir qualquer arquivo GreenSock, especialmente pelas restrições a editores visuais.
- Manuais para LLMs ficam em `docs/LLM_*.md`; exemplos JSON devem passar por `schema.normalize` e regressões automatizadas antes de publicação.

## Ponte GIL 0.2.1
- O adaptador GIL produz mídia local e fonte verificável, sem escrever o JSON automaticamente. Persistência e edição continuam no serviço canônico do vídeo; narração e faixas existentes nunca são substituídas implicitamente. Nenhum código de projeto deve ser executado pelo importador JSON. O editor GIL permanece autoridade dos objetos internos. Preservar os contratos do SpatialSeed e explicitar limites de projeção.

## Controle temporal V3.7
- Alterações coletivas de duração são planejadas e validadas integralmente antes de alteração, sem tocar mídia, voz e fontes GIL. A duração mínima é um atributo do documento; velocidade de reprodução é estado efêmero da interface. Preserve o encaixe de voz no renderizador.
- O clip HTML segue o tempo lógico da cena e pausa durante espera por voz; carregamento de metadata e seeks assíncronos não devem introduzir relógio concorrente. O derivado MP4 da GIL não equivale à execução nativa do objeto.

## V3.8 — autoria e organização
- Planejamento temporal usa o mesmo `voice_required_seconds()` do renderizador. Medir não grava; aplicar exige snapshot íntegro e só altera durações. Voz ausente fica intacta. Redução pode encurtar outras trilhas e clipes; não apaga arquivos.
- Projeto arquivado é JSON preservado em `projetos/.arquivados`, com nome reservado. Operações exigem confirmação, origem local, ausência de tarefa ativa e não sobrescrevem. Mídia/cache compartilhados não são coletados ou movidos automaticamente.
- Inventário usa referências do documento, não varredura de diretórios privados. A biblioteca utiliza as faixas existentes, IDs próprios e o pipeline canônico SVG; a ponte GIL permanece dona do derivado, com fonte preservada. Não duplicar contratos de animação/voz ou executar código arbitrário.

## GIL nativa V3.10.1 experimental
- A camada opcional `gil_nativo` preserva fonte e digest sem exigir `video_clipe`. O relógio é o do editor/player; módulos do runtime GIL instalado são servidos por allowlist local. Não duplicar o compilador. O caminho legado e mídias existentes permanecem. Não exportar/publicar visual incompleto; composição com áudio GIL, assets externos e exportação direta ainda requerem integração. Testar em projeto de cópia antes da integração.

## GIL nativa V3.10.2
- Demonstração silenciosa autocontida; importação volta ao início da cena, abre a prévia e informa o estado. GIL3 3.0 tem gramática própria: não confundir extensão com conversão nem prometer animação de fonte estática.

## V3.11 experimental · objetos de mídia
- `objetos_midia` é opcional, com IDs únicos por cena, imagens, clipes mudos e composições GIL silenciosas. Não altera duração de cena nem áudio na inserção. Ordem da lista define empilhamento sobre as camadas legadas. Movimento externo usa um documento GIL (grupo `media`), avaliado no tempo local pelo mesmo Timeline; nunca `eval`. Não anunciar exportação visual até compositor final validado. Alterações puramente visuais não devem invalidar o transporte de áudio salvo. Preservar fonte e referências locais de mídia.

## V3.12 experimental — exportação web
- Exportar a composição do documento em canvas com MediaRecorder, sem intermediários MP4/PNG. Preservar o pipeline legado. A projeção de mídia usa o mesmo `motionProgram`, `rect` e `prepare` da GIL; não introduzir interpolador. O mix de áudio reutiliza o motor existente e a duração nominal do documento; nunca truncar voz excedente silenciosamente. A gravação em tempo real é experimental, não determinística; informar quadros desenhados e falhar em atraso persistente. Não confundir este caminho ainda dependente de `/api/preview` e mix Python com o objetivo estático. Não tratar a fusão GIL3/GIL/SpatialSeed como pré-requisito da primeira exportação.

## V3.12.1 experimental — transporte e exportação longa
- A duração efetiva da prévia e da exportação web segue `scene_length`, inclusive `encaixe_voz` e arredondamento de áudio legado. Não alterar duração nominal nem criar voz automaticamente. Na extensão, manter a última pose nominal, sem retemporizar animações. Player V3 continua preservado como referência, ainda não unificado.
- Para exportações longas, mix WAV servido com token efêmero e Range, áudio em streaming, somente cena atual/seguinte carregadas e fragmentos do MediaRecorder em OPFS. Sem codificação intermediária de vídeo. Erros de sincronização/armazenamento interrompem o trabalho. Não afirmar gravação de dez minutos validada antes de teste real. Arquivos de vídeo de entrada e projetos não são apagados.

### V3.12.2 — composição de movimentos e áudio de mídia
Consultar `docs/CLIP_AUDIO_MOVIMENTO_V3122.md`. Não duplicar o áudio de câmera já incorporado à locução. A assinatura de áudio inclui somente os parâmetros sonoros/temporais dos clipes, não a pose ou a fonte GIL. A prévia e a exportação usam a mesma função de mixagem de cena; manter compatibilidade com o clipe original e com `motion`. Testar antes de promover: `python -m unittest discover -s tests` e `RD_GIL_ROOT=/caminho/confirmado/gil node --test tests/*.mjs`.

### V3.13.0 — viewport e plataforma agnóstica
Consultar `docs/VIEWPORT_PLATAFORMA_V313.md`. A matriz afim é compartilhada entre seleção, DOM e Canvas; campos novos opcionais. Não criar outra linguagem nem outro interpolador de tempo. APIs detectadas só se tornam backends selecionáveis quando há implementação e contrato testados; fallback deve conservar o conteúdo, informar limitações e não publicar ou produzir mídia incompleta. Medir performance no dispositivo antes de trocar motores. Preservar projetos, áudio, Player V3 e Ateliê. Revisão visual no Android antes de integrar.

### V3.13.1 — viewport com ferramentas acessíveis
- Barra compacta de ferramentas visível sobre o viewport: seleção, mover, escala, rotação, cisalhamento, pivô, inserir e inspecionar. Ferramentas não são menus de cenas e não alteram o áudio.
- Arraste direto do objeto respeita o modo escolhido; alças de precisão da seleção continuam disponíveis. Alças são alvos de toque com `touch-action:none` para evitar scroll concorrente. O preview usa a mesma matriz afim dos objetos persistidos.
- Em todas as próximas entregas, encerrar a resposta com um checklist objetivo de ações a executar e resultados a observar no Android. Testes isolados de DOM/Chromium não substituem validação no dispositivo. Revisão local antes de commit/push.

### V3.13.3 — exportação e viewport (experimental)
- A ferramenta de transformação é única: arraste do corpo translada e alças editam dimensões, rotação, cisalhamento e pivô. Barra e opções de empilhamento pertencem à interface, nunca ao quadro exportado.
- HTML independente com GIL incorpora exclusivamente módulos autorizados do runtime instalado (`RD_GIL_ROOT`) e mídias locais referenciadas, sem buscar recursos externos. Se faltar qualquer dependência, interromper em vez de gerar HTML parcial.
- O modo Apresentar deve utilizar os mesmos `syncObjects`/`updateLayer` do editor. Captura de tela usa `getDisplayMedia` apenas quando disponível e com gesto/permissão explícita; exportação Canvas pelo editor permanece o fallback no Android.
- Após aplicar, validar em Android os gizmos, seleção, ordem de camadas, áudio, apresentação, gravação/exportação e HTML offline. Não publicar automaticamente.

### V3.13.4 — execução convergente, áudio e seleção legada
- `web/media-start-gate.js` coordena `play()`/`pause()` de áudio HTML no editor, na apresentação e nos HTML autônomos. Toda Promise de `play()` deve ser tratada; não mascarar falhas reais de permissão, codec ou mídia. O HTML autônomo precisa atribuir explicitamente o URI incorporado ao elemento de áudio antes de reproduzir.
- O clipe original permanece no esquema legado até ação humana **Converter clipe em camada editável**. A ação transfere arquivo, pose e áudio para `objetos_midia`, removendo sua referência ativa do `video_clipe` para impedir duplicação. O histórico do documento deve permitir desfazer.
- Seleção de SVG legado abre ferramentas existentes de SVG/animação, preservando IDs. Não gravar mudanças temporárias no SVG da prévia como se fossem edição persistente.
- Programas de movimento usam exclusivamente `motionSource`/`motionProgram` com `Timeline` GIL; múltiplos programas podem coexistir. `visual-effects.mjs` contém a apresentação de moldura, cantos e sombra para DOM e Canvas. Evitar criar efeitos incompatíveis entre exportadores.
- O pipeline legado de frames SVG não está unificado com a avaliação nativa de objetos; não afirmar unidade completa de renderer até retirar a duplicação com testes de paridade. Testar vídeo de 10 min e áudio no Android antes de promover estabilidade.

## M1a — interface integrada (experimental)

- O documento, runtime audiovisual e exportadores existentes permanecem como fonte de verdade: `studio-layout-v1.js` gerencia **somente apresentação e navegação**, nunca quadros ou áudio.
- Movimentar nós DOM já vinculados não altera seus IDs/handlers. A alteração do layout deve preservar `previewPanel`, `videoTimelinePanel`, `scenesPanel`, `editPanel`, `workPanel` e `objectInsert`.
- A barra de transformação só deve ser mostrada na composição e não durante a abertura de painéis externos.
- Inserção pela biblioteca exige prévia/confirmacão; recursos incompatíveis não são convertidos silenciosamente.
- Testar em Android retrato/paisagem, validar áudio, clipes, exportação, salvar/reabrir e undo/redo antes de commit ou push.

## RD Studio M1b (experimental)
- Títulos são criados como PNG transparente importado pelo mesmo fluxo de `objetos_midia` do tipo `image`; os movimentos são programas GIL do runtime existente. Não criar segundo renderer ou relógio para títulos.
- A conversão explícita da imagem legada para objeto independente preserva a mídia e usa histórico do documento. Recortes ativos não podem ser descartados silenciosamente; a conversão é bloqueada nesse caso.
- Transformação SVG no viewport atua somente sobre elementos com ID persistido na fonte SVG e serializa mudanças no documento; ferramentas vetoriais avançadas permanecem no Ateliê.
- Editor de fonte GIL embutido valida com `gil-native.mjs` e nunca pressupõe uma porta de serviço. GIL3 e áudio GIL continuam fora do contrato.
- Antes de integrar, verificar importação, seleção, transformação, desfazer/refazer, áudio e exportação no Chrome Android. Não fazer commit/push sem aprovação.

## M1d — Roteiro 0.2 e estilos (experimental)
- `web/roteiro-v02.mjs` compila a linguagem Roteiro 0.1/0.2 para GIL Timeline 0.1; **sem relógio, player ou renderizador próprios**. `web/roteiro-editor.mjs` é apenas interface e usa `scene-object-editor.openSource()` para inserir mediante confirmação.
- O catálogo `web/roteiro-styles.mjs` contém perfis próprios de aparência e movimentos, sem copiar prompts, assets ou scripts das bibliotecas externas. `docs/ROTEIRO_02.md` registra fontes e limites.
- Fontes Roteiro editáveis não são persistidas no JSON: salvar/importar arquivo `.roteiro` separadamente; o JSON guarda a fonte GIL compilada. Não afirmar o contrário.
- Preservar o comportamento de áudio e transições das versões anteriores e os limites reais do runtime GIL. Não usar eSpeak nas demonstrações.

## V3.14.4 — Roteiro 0.3, planos de agente (experimental)
- O script 0.3 estende 0.2 sem executar JavaScript. As diretivas para clipes, áudio e transições apenas planejam alterações tipadas na cena; uma simulação integral e confirmação humana precedem a aplicação.
- O plano JSON `rd-studio-plan-0.3` aceita apenas operações em campos conhecidos; mídia deve existir no documento, e clipes legados precisam ser convertidos explicitamente para `objetos_midia`. Nunca buscar arquivos externos, publicar, exportar ou executar comandos em nome do plano.
- Transformações e transições por objeto usam `scene-objects.mjs`/GIL; fades de áudio usam os campos já lidos pelo mixer. Crossfade entre cenas continua não implementado. Não introduzir motor paralelo de renderização, áudio ou temporização.
- O editor Roteiro 0.3 separa `seekScene` (cursor da cena) de `seekSlider` (prévia), evitando importação inválida do módulo.


## Roteiro 0.4 / Catálogo paramétrico experimental
A evolução 0.4 reutiliza o runtime GIL, o mixer e o histórico. Operações sobre projetos exigem simulação, IDs explícitos e confirmação. Não afirmar que LaTeX, importação automática de packs de terceiros, crossfade inter-cenas ou edição DOM arbitrária estejam implementados. Licenças variam por asset. Ver docs/ROTEIRO_04_CATALOGO.md.
