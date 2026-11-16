# GIL Timeline 0.2 — RD Studio Lab

Versão atual de autoria e exportação: [../docs/AUTHORING_V020.md](../docs/AUTHORING_V020.md). O restante registra o laboratório 0.1 e suas limitações originais; o novo servidor é `python tools/local_server.py --port 8791`.

Protótipo executável para consolidar a autoria declarativa GIL3 e o runtime procedural do SpatialSeed. Autoria principal: Rogério Duarte. Assistência: OpenAI GPT. Não é uma nova versão dos editores originais. Nenhuma dependência externa, instalação npm ou publicação Git necessária.

## Executar

`node --test tests/lab.test.mjs` (Node 22+) e `python -m http.server 8791 --bind 127.0.0.1` na raiz deste diretório; abrir http://127.0.0.1:8791/. Use Ctrl+C para encerrar. Som requer gesto do usuário. Para gerar HTML autocontido, `python tools/build_portable.py caminho-novo.html`.

## Recuperação e proveniência

Auditoria GIL 16/11/2026: 225 arquivos verificados por SHA-256. Auditoria integração 14/11/2026: 809 arquivos verificados; SpatialSeed HEAD `206b9a9cc7722d3f2a45b5f13237b47aac881bca` (o snapshot pode incluir mudanças locais). Histórico GIL contém `.gil`, `.gil2`, `.gil3`, viewers e variantes de compiladores. Selecionamos `home/r1/gil3_compiler_experimental.py`, testado com helix, amb, brasília, flora e floco 001. `g3c.py` falhou em amb; variante Downloads falhou nos cinco. As versões não são automaticamente intercambiáveis. Os arquivos selecionados e dez módulos originais do SpatialSeed são cópias não modificadas identificadas em PROVENIENCIA.json. O arquivo package.json do vendor só habilita ESM em Node, não é o manifesto upstream. Não publicar o vendor sem revisar licença e atribuições originais.

## Arquitetura

`language.mjs` (parser/IR expandida) → `model.mjs` (serviço editorial e validação pelo PropertyRegistry, identidade OccurrenceRef e RuntimeCapabilities) → `timeline.mjs` (TemporalRuntime, AnalyticTimeDomains, expressões afins, matrizes) → adaptadores `render-svg.mjs` e `audio.mjs`. `ui.mjs` não escreve diretamente no documento; chama o serviço e projeta resultados. A pose vem da avaliação analítica a cada t, sem gravar quadros no documento. Undo/redo atua sobre revisões editoriais. `examples/orbit.gil` tem 39 objetos, 18 faixas, 8 cues e 30 segundos. Arte original da GIL3 é pré-compilada para SVG; não há importação sem perdas do grafo GIL3.

O documento admite tipos de recursos arbitrários com propriedades escalares declaradas; o tipo determina somente as capabilities disponíveis no adaptador. A telemetria `arbitrary.telemetry` preserva identidade, estado, unidade, valor animado e edição mesmo sem adaptador visual. Ainda não implementa recursos gerais do world-model SpatialSeed nem plug-ins de terceiros. Instâncias têm id global e caminho hierárquico; não existe instanciamento de subárvores com slots equivalentes ao world-model completo.

## DSL experimental (não substitui a gramática GIL3)

Um comando por linha; comentários `//` apenas em linhas próprias; cabeçalho `gil timeline 0.1 {`, encerramento `}`. Argumentos complexos são JSON válido. `stage {"width":960,"height":540,"duration":30,"background":"#08142b","camera":"cam"}`. `resource ID TIPO {propriedades}` declara recurso, `object ID RESOURCE PARENT {overrides}` cria ocorrência; `-` significa sem pai. Propriedades básicas x,y,z,rx,ry,rz,sx,sy,sz,opacity,layer existem em todos; outras chaves são declaradas no recurso, tipos string/number/boolean fixos globalmente. `repeat PREFIX RESOURCE PARENT COUNT {overrides}` permite `{"expr":"..."}` em valores; `i` começa em 1, `count`, `u` normalizado; gera IDs PREFIX_1 etc. No documento editado visualmente, repeat fica expandido na serialização; preserve a fonte original para recuperar o procedimento. `animate ID PROP {"expr":"...","start":0,"end":30}`; ou `{"keys":[[0,0],[30,1]],"ease":"smooth"}`. Tempo t em segundos, u normalizado no intervalo e v valor-base; antes do início vale o estado base; depois, valor no fim. Uma faixa por propriedade; sem sobreposições. Trigonometria em radianos, rotações em graus. A linguagem afim original também oferece pi, tau, sin, cos, mix, smoothstep etc. Erros matemáticos em instantes futuros são explicitados, não há prova estática de totalidade. `cue ID {"start":5,"duration":0.2}` para `audio.tone`. Limites: 512 objetos, 1024 faixas, 128 recursos/cues; profundidade 64; duração 600 s. A expressão não autoriza JS livre, rede ou acesso ao DOM.

### Console e inspeção

`select ID` e `move dx dy dz` sobre a seleção única são compatíveis com o subconjunto de sintaxe do DevConsole; deslocamento mundial no documento-base, incluindo pai rotacionado. `set ID PROPRIEDADE JSON` e `move ID [dx,dy,dz]` são extensões de laboratório; o último usa coordenadas do pai e aceita expressões escalares afins. `undo`, `redo`. Outros comandos do SpatialSeed ainda não estão presentes: seleção múltipla, pivot, rotate/scale coletivos, ferramentas, procedimentos SES e commits no sandbox. A integração real deve encaminhar as intenções aos comandos públicos existentes (selection.translate, selection.properties.*, history.*, program.plan.commit), com validação de revisão, não replicar seus efeitos. O registro do laboratório não substitui o registro do runtime do SpatialSeed.

### Projetos e publicação

A fonte GIL e IR JSON podem ser baixadas; SVG de um quadro contém as imagens GIL3 incorporadas. A demo HTML autocontida é um artefato estático próprio e pode ser estudada como futura publicação editorial, não publicada automaticamente. Na V3.6 o sanitizador SVG aceita data:image/png/jpeg/webp mas não SVG incorporado em image; portanto não se deve afirmar que quadro exportado mantém a arte ao importar no editor atual. É necessário um adaptador de mídias e exportação audiovisual validado contra schema.py, svg_graphic.py e studio_core.py. O JSON GIL não é o JSON de projeto Estúdio SVG e não deve ser enviado ao seu endpoint de importação. RD Studio mantém prévia e administração separadas; não atribuir token CSRF, acesso a Git ou FS a um applet. Um futuro gerador RD Patch deve respeitar hashes, escopo e limites atuais; nenhuma alteração nesse mecanismo aqui.

### Limites deste marco

3D é projeção em perspectiva de cubos via SVG (painter, sem clipping robusto, PBR ou WebGL), luz direcional simples, 2D é overlay de tela, câmera do documento separada da UI. Renderização recompõe SVG a cada frame; instancing de GPU e processamento incremental de render ainda não integrados. Efeitos são tons sintetizados com Web Audio, agenda temporal e cancelamento; não existe mixer de arquivos/narração ou sincronização amostral com vídeo; relógio visual usa performance.now. Não há MP4, importação de arbitrary asset ou seleção múltipla. Sem persistência automática, exporte GIL antes de fechar. Seleção, edição de propriedades e timeline (seek) testadas; áudio físico e Termux ainda pendentes. O runtime de animação especializado TemporalAnimationRuntime não é usado nesta etapa: usa-se a abstração temporal de nível inferior já existente, preparando o adaptador real.

## Próximos gates (não implementados)

1. Validar no Termux e fixar revisões reais, consolidar repo de integração aprovado.
2. Adapter do DevConsole/sandbox/Caps do SpatialSeed, sem autoridade duplicada, e projeção WebGL nativa via RenderNode/RenderDelta.
3. Preservar GIL3 como AST de autoria de recursos/âncoras, mapear instâncias para OccurrenceRef sem achatamento prematuro; mapear documento V3.6 e catálogo editorial.
4. Mixer de áudio importado, sons e narração; relógio de reprodução comum; keyframes/timeline, transições, seek, export frame determinístico por backend.
5. Integração RD Studio por adaptador protegido, publicação/exportadores HTML/MP4, testes diferenciais e gates próprios do SpatialSeed.
