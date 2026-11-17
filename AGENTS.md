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
