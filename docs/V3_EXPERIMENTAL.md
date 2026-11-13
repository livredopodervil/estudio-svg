# Estúdio SVG — V3.0.0-alpha.1 (experimental)

**Base estável:** V2.7.4.1, commit `b6f3b3e`, branch `main` do repositório `livredopodervil/estudio-svg`. A V3 não substitui essa base. Autor do Estúdio SVG: Rogério Duarte; preservar licenças/créditos de terceiros.

## Escopo realizado — primeiro marco técnico

- `tipo: "espacial"` é **opcional**. Cenas dos oito tipos antigos continuam com o mesmo esquema e pipeline.
- Módulo isolado `spatial_scene.py`: contrato validado, câmera 3D, sólidos cubo/esfera/pirâmide, cores, posição/rotação/escala, 32 objetos no máximo, 64 faixas de keyframes no máximo.
- Projeção geométrica 3D com sombreamento simples convertida em **SVG**. O mesmo gerador alimenta a prévia e os quadros codificados pelo FFmpeg; animações são funções do tempo absoluto normalizado, sem relógio ou estado acumulado.
- Editor responsivo `/espacial?name=NOME&scene=NUMERO`: seleção, duplicação/exclusão, mudanças de posição/rotação/escala/câmera e avanço temporal; não altera o projeto persistido até o botão **Salvar**.
- Comandos JSON declarativos limitados a `adicionar`, `alterar`, `excluir` e `animar`, validados no backend. **Não há execução de JavaScript arbitrário.**
- Cena pronta de demonstração: `examples/espacial_v3_experimental.json`.

## O que ainda NÃO está implementado

- Importação direta do formato `.spatialseed`, reutilização do motor Three.js, edição de vértices/arestas/faces, materiais PBR, sombras reais, texturas 3D, múltiplas luzes, física ou sandbox completo de scripts.
- Gizmos 3D manipulados diretamente no viewport; nesta primeira entrega os objetos são editados pelos controles numéricos. O viewport mostra o resultado das transformações.
- Renderização GPU/WebGL; o MVP projeta geometria 3D básica em SVG para compatibilidade determinística com o atual pipeline.

**Critério de aceitação:** gerar MP4 vertical com cubo em rotação, quadro inicial/final previsíveis e 40 testes legados preservados. Performance no Android real pendente de validação.

## Contrato JSON — fragmento de cena

```json
{
  "tipo": "espacial",
  "duracao": 5,
  "espacial": {
    "camera": {"azimute": 25, "elevacao": 18, "distancia": 10},
    "objetos": [
      {"id":"cubo", "tipo":"cubo", "posicao":[0,0,0], "rotacao":[0,0,0], "escala":1, "cor":"#e8a96e"}
    ],
    "animacoes": [
      {"alvo":"cubo","propriedade":"rotacao_y","inicio":0,"fim":1,"de":0,"ate":360,"easing":"linear"}
    ]
  }
}
```

Propriedades de faixa: `posicao_x`, `posicao_y`, `posicao_z`, `rotacao_x`, `rotacao_y`, `rotacao_z`, `escala`. Cada faixa utiliza `inicio` e `fim` entre 0 e 1; `de` e `ate` são valores absolutos da propriedade (não deltas). `easing`: `linear` ou `suave`. IDs de objetos devem ser únicos.

## Exemplo de comandos JSON de LLM

```json
{
  "operacoes": [
    {"op":"adicionar", "id":"sol", "tipo":"esfera", "cor":"#e9bb55", "posicao":[0,0,0]},
    {"op":"animar", "alvo":"sol", "propriedade":"escala", "inicio":0, "fim":1, "de":0.2, "ate":1.3}
  ]
}
```

`alterar` aceita apenas `campo` igual a `cor`, `posicao`, `rotacao`, `escala` ou `visivel`; `excluir` remove o objeto e suas faixas. Limites do backend são aplicados antes da alteração em memória.

## Instalação e reversão

Execute somente sobre uma worktree V3 **criada a partir do commit estável verificado**. Não faça merge automático nem push na `main`. Para abortar a instalação antes de criar commits, execute `git apply -R --check <patch>` e então `git apply -R <patch>`, desde que nenhum dos arquivos tenha sido alterado após a instalação. Para reversão de um commit V3 dedicado, use `git revert` na branch experimental.

## Próxima etapa: adaptador SpatialSeed real

Inspecionar contratos e licenças dos módulos de `livredopodervil/SpatialSeed` no commit fixado, definir tradução explícita de identificadores, hierarquias, comandos e animações para o esquema acima. Somente depois adicionar o renderer WebGL opcional e medir GPU/memória no Android. O presente módulo é um **marco interoperável**, não uma incorporação do código SpatialSeed.
