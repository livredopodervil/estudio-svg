# RD Studio M2 — cena unificada SpatialSeed / GIL / SVG

**Estado: projeto iniciado, contrato e protótipo de roteamento testados; NÃO integrado ao viewport real.**

## Objetivo

Um único documento lógico de composição controla objetos SpatialSeed 3D, vetores SVG,
texto, áudio, mídia e UI, por um único relógio da timeline do Studio. A câmera SpatialSeed
continua editável. Nenhum MP4/WebM intermediário deve ser necessário para uma cena 3D.

## Fonte de verdade e independência dos repositórios

- SpatialSeed mantém seu repositório, runtime Three.js e API. O Studio carrega um commit
  identificável de `main`; atualizações são explícitas, verificadas e reversíveis.
- GIL fornece avaliação temporal e linguagem de animação; não duplicar o compilador.
- O documento Studio guarda identidade, hierarquia, referências, poses, eventos e a política
  de vinculação (externo por versão/digest ou cópia incorporada). A migração de projetos
  nunca executa scripts arbitrários ou resolve URLs externas automaticamente.

## Contrato M2.0 (protótipo, em `web/studio-shared-scene.mjs`)

- `objectRef(space, id)`: `space` = `spatialseed`, `svg` ou `media`, e `id` é estável.
- `sceneEvent({type,source,target,payload})`: evento tipado com origem, alvo e dados.
- `createSharedSceneBridge(adapters).at(t,operations)`: recebe **t do Studio**;
  distribui `seek(t)`, operações avaliadas e `renderAt(t)` aos renderizadores existentes.
- O protótipo não avalia código GIL e não altera o motor SpatialSeed. Não é um novo relógio,
  renderer, ou runtime independente. Ações são validadas antes do primeiro efeito.

## Marcos de implementação (ordem)

1. **M2.0 — Contrato**: IDs, tempo externo, operações e eventos tipados (protótipo criado).
2. **M2.1 — Adapters reais**: ligar `seek`, `set`, eventos e consulta de propriedades ao
   SpatialSeed `main`, SVG e GIL, com testes de paridade e Android retrato/paisagem.
3. **M2.2 — Autoria sincronizada**: objeto 3D dispara evento no painel SVG; edição de uma
   propriedade externa move objeto 3D; câmera e objetos com keyframes observáveis.
4. **M2.3 — Projetar 3D em SVG**: exportação explícita de grupos identificáveis por objeto;
   documentar aproximações de malhas/PBR e alternativas raster/WebGL para efeitos não vetoriais.
5. **M2.4 — Exportação determinística**: renderizar por tempo lógico via mesmo estado do
   viewport; compor camadas/áudio, medir diferença de quadros e não remover gates antes da validação.

## Critérios de aceitação

- Cena com núcleo procedural e duas legendas: os núcleons movem-se no WebGL, um evento GIL
  altera SVG no mesmo instante e o cursor da timeline reproduz qualquer quadro.
- Arrastar câmera ou alterar FOV persiste após salvar/reabrir; animações de câmera em 9:16 e 16:9.
- Exportação representa o mesmo estado visual da prévia; ausência de frames incompletos,
  sem vídeo intermediário e com áudio presente.
- Compatibilidade com projetos SVG antigos e importação de mídia faltante, inclusive
  preservação de referências; testes Android antes de publicação de cada marco.

## Segurança / publicação

Patch incremental em worktree; nunca trabalhar sobre cópias presumidas. Nenhum push M2 até
aprovação dos testes e da prévia. Registro de SHA-256, HEAD e dependências em cada marco.
