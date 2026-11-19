# M1W — SpatialSeed main no Estúdio SVG

Projeto de Rogério Duarte. Integração local experimental; nenhuma publicação remota.

## Fonte de verdade

A instalação requer um clone Git **separado** de `https://github.com/livredopodervil/SpatialSeed.git`, branch `main`, HEAD registrado no teste. O conteúdo da árvore original não é alterado nem copiado no repositório do Estúdio. Dependências e créditos permanecem na fonte original.

## Capacidades desta etapa

- Viewport WebGL com o renderer **ThreeRegionRenderer** do SpatialSeed real, mais seleção, edição, ferramentas e console procedural originais dentro do mesmo espaço visual do Estúdio.
- Abrir/salvar `.spatialseed` pelo importador/exportador da própria versão GitHub main, sem converter para SVG/GIL.
- Capturar o canvas WebGL com MediaRecorder e inserir o WebM como clipe na cena atualmente selecionada do Estúdio. Seu pipeline de exportação existente poderá usar esse clipe, sem reimplementar motores.
- Captura não inclui áudio (a trilha sonora/narração permanecem no Estúdio). O WebM é gerado em tempo real pelo navegador; o resultado depende da performance GPU e da animação ativa.

## Limites ainda não cobertos

Este marco compartilha o renderer para uma estação WebGL integrada e importa sua saída para a timeline por **clipe**; NÃO há ainda reprodução determinística arbitrária da cena SpatialSeed em cada instante da timeline, edição de cada objeto 3D pelo inspector 2D do Estúdio nem exportação frame-a-frame sem clipe. Para equivalência editável entre prévia e exportação, serão necessários contratos estáveis de estado/câmera/tempo e os módulos do SpatialSeed main completo. Esta entrega não anuncia essas capacidades como implementadas.

## Prévia Android

Criar clone isolado, sem tocar seus outros checkouts:

```sh
mkdir -p "$HOME/.local/share/rd-studio"
git clone --branch main --depth 1 https://github.com/livredopodervil/SpatialSeed.git "$HOME/.local/share/rd-studio/spatialseed-main"
git -C "$HOME/.local/share/rd-studio/spatialseed-main" rev-parse HEAD
```

Checar `vendor/three.module.js` e `apps/web/index.html`. Configurar ambos os caminhos:

```sh
cd "$HOME/estudio_svg_v3_git"
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" \
RD_SPATIALSEED_ROOT="$HOME/.local/share/rd-studio/spatialseed-main" bash iniciar.sh
```

Abrir no próprio Android: `termux-open-url 'http://127.0.0.1:8771/'`.

## Critérios de aceite

1. O botão **SpatialSeed WebGL** abre e fecha o viewport sem perder cenas.
2. Abrir um `.spatialseed` válido permite orbitar, selecionar e alterar objetos no renderer original.
3. O console original executa `create box size 2 1 3` e `animate spin speed=45 axis=y`, após seleção apropriada.
4. Capturar 7 segundos anexa WebM na cena selecionada, sem alterar a fonte 3D do SpatialSeed.
5. Salvar e reabrir o projeto Estúdio mantém o clipe; exportação web inclui os quadros gravados.
6. Verificar que arquivo 3D não compatível não altera o Estúdio e que uma mudança de cena durante upload bloqueia associação à cena errada.
7. Verificar responsividade no Android, áudio, menu Mais e editor de objetos. Testes humanos pendentes.

## Continuidade

O arquivo `AGENTS.md` existente é preservado. Documente o commit real main do SpatialSeed e a aceitação humana antes de qualquer push.
