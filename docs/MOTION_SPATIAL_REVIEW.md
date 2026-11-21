# Integração inicial de movimento e SpatialSeed

Autoria do Studio e SpatialSeed: Rogério Duarte. Base do Studio 6eaacb06dff74f88d34b5b92598be1f33822380b, branch feat/studio-shared-scene-m2. SpatialSeed main e50dc66f883ee1b3faad769457ad6ca6f819506c. Os patches são independentes para revisão. Não houve commit ou publicação.

## Autoria e implementação

* Motionmaxxing, Tejash Makwana, https://github.com/Tejashmakwana/motionmaxxing em 8c8ec0f2a6f6c9a0da15cd24f7b1298ab298368c. O preset word-rise usa a ideia de entrada escalonada de palavras com desaceleração. A implementação usa faixas SVG do Studio. Nenhum código, asset ou runtime GSAP foi importado.
* Claude Animation, Hanif, https://github.com/buildwithhanif/claude-animation-skill em 4ddb8c80fdec96dc9f55d4b9bdee60bde6f0134b. O preset beetle adapta a silhueta, a disposição dos membros e a alternância de fases de lib/rigs/bug.mjs para vetores e seis faixas articulares. A licença e o crédito estão em docs/licencas/claude-animation-MIT.txt. O catálogo e o Ateliê existentes servem para inserção e edição. Ainda não há backend genérico de Canvas procedural ou importador de skills.
* examples/motion_spatial.json reúne as duas animações, um cubo nativo e três poses de câmera em quatro segundos. A demonstração é silenciosa.
* O transporte fornece segundos locais, limitados à duração nominal durante extensão de áudio. O adaptador pausa e posiciona o domínio world e verifica o retorno antes da câmera. Física de jogo, entradas externas, domínios independentes, scripts com estado e relógios de áudio internos não têm garantia de rebobinagem. O Studio continua usando o transporte de áudio existente.
* A fonte original e as edições capturadas permanecem no JSON. Ao editar no viewport, use **Capturar edição 3D na cena** e depois **Salvar**. A captura é explícita: trocar de cena antes de capturar pode descartar alterações 3D. A cópia física fica em projetos/spatialseed/<sha256>.spatialseed e no ZIP portátil em spatialseed/. Versões idênticas são deduplicadas. O importador reconstrói a cópia a partir do JSON normalizado. A exclusão, renomeação e movimentação de projetos não apagam essas fontes compartilhadas.
* O Studio abre o mundo pela resposta de project.open. Com o patch SpatialSeed, viewer.frame.capture entrega ImageBitmap do render nativo. Exportação offline requer a consulta disponível. Exportação em tempo real mantém a captura por stream para versões com os comandos temporais da base e sem a consulta nova. Os quadros nativos e as sobreposições compartilham a composição. A gravação em tempo real pode perder quadros. Os exportadores legados de HTML e MP4 mantêm as limitações da base.

## Verificação e retomada

No kit, preparar.sh instala cópias de revisão dos dois commits. abrir.sh inicia a porta 8782. As variáveis RD_STUDIO_SOURCE e RD_SPATIAL_SOURCE permitem escolher fontes Git locais que contenham os commits. Sem elas, a primeira instalação consulta os repositórios públicos. RD_GIL_ROOT pode apontar para o GIL já instalado. Os projetos de trabalho existentes não são copiados. Se o teste precisar deles, importe uma cópia pelo editor.

Abra /?project=motion_spatial, alterne entre 0,25 s e 2 s e volte. Observe texto, seis pernas e enquadramento. Abra /verificar-motion e execute o teste com aba visível. O teste lê o relógio nativo e compara hashes de pixels para WebGL e composição. Exige A=C, A diferente de B e diferença entre cada quadro composto e o WebGL isolado. Uma falha informa o estágio ou o erro. A resolução do GPU e as fontes do aparelho podem alterar hashes entre máquinas. Compare dentro da mesma execução.

Após editar o cubo, capture a edição, salve, reabra e confira o ZIP. Exporte pelo navegador em modo offline e compare os mesmos instantes com o editor. Em cópia de um projeto com voz, teste também A/V, pausas, fim da cena, retrato/paisagem e responsividade Android. Guarde os hashes exibidos, o aparelho, os FPS e a primeira falha. Não confunda a verificação automatizada local com aceite humano.

No checkout do Studio, execute:
```bash
python -m unittest discover -s tests -p 'test_motion_spatial.py'
python -m unittest discover -s tests -p 'test_studio_spatialseed_viewport.py'
node --test tests/test_workspace_v38.mjs tests/test_m22_offline_frame_handshake.mjs tests/test_studio_shared_scene.mjs tests/test_studio_spatialseed_camera.mjs tests/test_studio_spatialseed_panel.mjs
```
Os testes Node de composição também importam web/gil-runtime, uma ligação de teste para o GIL externo (não versionada). O servidor resolve os módulos via RD_GIL_ROOT. Reversão: encerre o servidor de revisão com Ctrl+C e volte ao checkout original. As cópias isoladas podem ser mantidas com seus projetos e fontes.
