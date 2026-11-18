# RD Studio — Roteiro 0.4 experimental: catálogo e edição incremental

Projeto: Rogério Duarte. Este incremento não altera a GIL Timeline, o player, o mixer, os exportadores, a geração de voz nem o esquema de projeto. Nenhum commit ou push automático.

## Funções implementadas

- **Catálogo original paramétrico:** 24 motivos geométricos × 12 paletas = 288 variantes; 8 configurações de título × 9 entradas = 72 variantes; 18 famílias de efeitos sonoros × 12 variantes de parâmetros = 216 WAV geráveis localmente. Total = **576 entradas parametrizadas**, não 576 obras criadas manualmente ou arquivos pré-gravados.
- As geometrias usam somente `shape.rect`, `shape.circle` e `text` existentes na GIL. Incluem seta, seta dupla, eixos, grade, gráficos, onda, espiral, diagrama de fluxo, rede, molécula, boneco etc. O diálogo usa `prepare` e `parseFrame` do player existente. Um elemento é inserido como **um objeto GIL** e pode receber seus movimentos e transformações habituais. Prévia a 35% do tempo, por enquanto estática.
- Os sons são WAV PCM mono originais, sintetizados apenas quando solicitados. Podem ser ouvidos, baixados e **importados pelo fluxo de áudio existente**. A galeria não modifica automaticamente a trilha do projeto, não cria outro transporte e não sintetiza voz.
- A seção Plano 0.4 aceita JSON declarativo sobre o **projeto inteiro**. Pode duplicar/reordenar cenas, alterar duração, texto e estado da voz, clonar/remover/reposicionar e estilizar objetos, além de delegar modificações de clipes, áudio e transições de objetos ao `previewScenePlan` 0.3 já existente. A operação é validada em cópia, exige confirmação, usa IDs estáveis, refusa comandos e propriedades desconhecidos e atualiza o histórico normal para Undo/Redo.
- As novas funções entram em Composição → `✧ Catálogo + Agente`. O repositório anterior e os projetos existentes não são convertidos.

## Exemplo: trabalhar de modo incremental

O agente pode produzir um plano pequeno, com precondições para não editar o documento errado:

```json
{
  "format": "rd-studio-project-plan-0.4",
  "expect": {"title": "Nome do projeto", "scene_ids": ["cena_001"]},
  "operations": [
    {"type": "scene.clone", "source": "cena_001", "id": "cena_002"},
    {"type": "scene.text", "id": "cena_002", "field": "titulo", "text": "Como funciona?"},
    {"type": "scene.duration", "id": "cena_002", "seconds": 9}
  ]
}
```

Para modificar um objeto existente em `cena_002`, há `object.clone`, `object.remove`, `object.position`, `object.appearance`. Para aproveitar as operações da cena na V0.3, existe `scene.edit03` com lista `operations` daquele contrato. O projeto precisa conter as referências corretas; nenhum ID ou arquivo é inventado.

## Limites e segurança

1. Ainda **não** existem novos codecs, curvas Bézier nativas GIL, texto LaTeX nativo, edição DOM de sites, sincronização por palavras, crossfade entre cenas ou sincronização audiovisual corrigida por este incremento. Nenhuma dessas capacidades deve ser declarada pronta.
2. LaTeX merece um próximo adaptador: **MathJax TeX→SVG** (Apache-2.0), empacotado offline, com fonte LaTeX armazenada num campo versionado e SVG rasterizado somente na exportação quando necessário. O backend deve ser determinístico e evitar carregamento de scripts externos. KaTeX (MIT) pode servir de prévia editável quando o compositor adotar o SVG gerado pelo mesmo processo.
3. Unicode é aceito no texto GIL (e no gerador de títulos existente por graphemes com `Intl.Segmenter`). A cobertura final depende das fontes disponíveis no Android e no renderizador offline. Recomenda-se importar subconjuntos de Noto licenciados sob OFL 1.1 com fallback explícito, e incluir as licenças no pacote.
4. Incluir imagens e sons **externos** requer importador com `sha256`, proveniência, licença, autor, atribuição, formatos aceitos e cache. Não se deve extrair em massa de um catálogo cuja licença varia por item.
5. O plano 0.4 não tem persistência autônoma nem permissões de agente; o usuário revisa, confirma e salva pelo editor. São mudanças incrementais no documento local, não uma API remota nem colaboração multiusuário.
6. O catálogo de 216 sons representa variações sintetizadas e curtas (aproximadamente 0,22–0,60 s). Sons realistas exigirão packs curados CC0 ou CC-BY e prévia de áudio no mesmo painel.

## Repositórios e licenças verificados em 17/11/2026

- Motion Canvas (MIT): https://github.com/motion-canvas/motion-canvas — animar por tempo e hierarquia de objetos.
- Manim Community (MIT): https://github.com/ManimCommunity/manim — matemática e didática, estudar arquitetura sem importar renderer Python.
- SVG.js (MIT): https://github.com/svgdotjs/svg.js — manipulação SVG.
- Rough.js (MIT): https://github.com/rough-stuff/rough — aparência artesanal/doodle.
- MathJax (Apache-2.0): https://github.com/mathjax/MathJax — TeX→SVG.
- KaTeX (MIT): https://github.com/KaTeX/KaTeX — prévia matemática.
- Lottie-web (MIT): https://github.com/airbnb/lottie-web — formato Lottie, requer integração específica.
- Tabler Icons (MIT): https://github.com/tabler/tabler-icons — mais de 6.200 ícones SVG.
- Lucide (ISC): https://github.com/lucide-icons/lucide — ícones vetoriais.
- Phosphor (MIT): https://github.com/phosphor-icons/core — mais ícones.
- Iconify (engine MIT, conjuntos independentes): https://github.com/iconify/icon-sets — verificar licença de cada pack.
- Kenney (CC0): https://kenney.nl/assets — personagens, sons, cenários e sprites.
- Quaternius (licenças por pack; verificar antes de usar): https://quaternius.com — modelos 3D.
- OpenMoji (CC BY-SA 4.0): https://github.com/hfg-gmuend/openmoji — importante avaliar obrigação de compartilhamento.
- Noto Emoji (OFL para fontes; subpastas têm licenças distintas): https://github.com/googlefonts/noto-emoji.
- ZzFX (MIT): https://github.com/KilledByAPixel/ZzFX — síntese leve para efeitos.
- jsfxr (Apache-2.0): https://github.com/mneubrand/jsfxr — gerador de efeitos.
- Tone.js (MIT): https://github.com/Tonejs/Tone.js — audio procedural; preservar o mixer/clock atual.
- Howler.js (MIT): https://github.com/goldfire/howler.js — sprites de áudio e gerenciamento; não criar um segundo mixer.
- Freesound (CC0/CC BY/CC BY-NC conforme arquivo): https://freesound.org — buscar e conferir permissões.
- Openverse: https://openverse.org — agregador que não verifica por si a correção da licença de cada item.
- OpenGameArt (licenças variáveis): https://opengameart.org — verificar cada asset.

## Critérios de teste antes do próximo commit

- [ ] Abrir `✧ Catálogo + Agente` somente em Composição; pesquisar setas, bonecos, símbolos, títulos e sons.
- [ ] Visualizar GIL → Inserir → Confirmar; cancelar não altera cena.
- [ ] Ouvir/baixar WAV; importar na trilha de efeitos já existente e exportar áudio/vídeo.
- [ ] Simular plano, cancelar; não alterar JSON. Confirmar plano, salvar, reabrir, desfazer/refazer.
- [ ] Clonar uma cena e alterar só seu título/duração, preservando áudio e objetos da original.
- [ ] Conferir casos negativos: objeto inexistente, cena inexistente, tipo de operação desconhecida, limite de 16 camadas e 150 cenas.
- [ ] Regressões: voz, mixagem, HTML autônomo, seleção, exportação web, passagem 2→3.

## Reversão

Usar `apply.py --revert` somente se os hashes pós-instalação coincidirem. O instalador nunca executa reset, clean, merge, push ou exclusão de projetos.

## Biblioteca de personagens e cenas, prioridade de curadoria

- **Open Peeps** (CC0, Pablo Stanley): https://www.openpeeps.com/ — silhuetas, roupas, cabelos e poses combináveis. Bom candidato para personagens 2D editáveis e rigging por grupos SVG; licenciamento confirmado no site oficial.
- **Kenney Mini Characters** (CC0): https://kenney.nl/assets/mini-characters — personagens e poses; também Toon Characters, UI e impactos. Bom candidato para sprites com atribuição opcional.
- **Google Material Design Icons** (Apache-2.0): https://github.com/google/material-design-icons — elementos de interface e pictogramas.
- **Public Code Illustrations** (CC0): https://github.com/publiccodenet/illustrations — ilustrações SVG reutilizáveis.
- **unDraw** possui licença própria que proíbe compilar e redistribuir as imagens como biblioteca concorrente; **não importar nem redistribuir em massa**: https://undraw.co/license.

O importador de pacotes deve armazenar `asset_id`, `sha256`, `provider`, `source_url`, `author`, `license_id`, `license_url`, `attribution_text`, `file`, `media_type`, `version` e `tags`, além de uma indicação de capacidade `commercial_allowed`. Os arquivos com licença ambígua devem permanecer em quarentena até análise humana. Armazenar um pack não autoriza republicá-lo como pack independente.
