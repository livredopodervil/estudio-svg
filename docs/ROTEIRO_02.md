# RD Studio — linguagem Roteiro 0.2 e estilos (experimental)

**Autoria:** Rogério Duarte. Assistência técnica: OpenAI. Base: Roteiro 0.1, projeto anterior do próprio RD Studio. A versão 0.2 compila exclusivamente para documentos **GIL Timeline 0.1** e usa o runtime GIL já existente. Não cria renderer, relógio, exportador, bibliotecas remotas nem executa JavaScript do roteiro.

## Acesso e operação

Em **Composição → Roteiro (☷)**, escolha um dos doze estilos de referência, digite título/subtítulo/duração e clique **Gerar base + roteiro do estilo**. O painel contém dois documentos distintos: **Fonte base GIL** (identidades, texto, objetos, paleta) e **Roteiro 0.2** (movimentos, ordem e instantes). **Compilar e visualizar** produz a GIL e uma prévia no tempo selecionado pelo slider. **Inserir GIL na cena atual** abre a mesma prévia/confirmacão de inserção utilizada pelos outros objetos GIL. Não há inserção automática sem confirmação. O projeto precisa ter uma cena aberta; o roteiro compilado deve caber nela.

A fonte base de um objeto GIL selecionado pode ser copiada para a edição. Objetos com animações GIL preexistentes não podem receber outra animação sobre a mesma propriedade; a compilação recusa conflitos. Ao importar uma base diferente, ajuste os IDs da linguagem de roteiro. **Salve o `.roteiro` separadamente**: o Estúdio persiste a GIL compilada no projeto, mas ainda não persiste a fonte Roteiro 0.2 editável. A fonte pode ser importada novamente pelo diálogo. Não há conversão reversa GIL → Roteiro.

## Gramática

```text
roteiro 0.2 {
  marca inicio 0s
  marca destaque 3.2s
  marca encerramento 6.6s
  em inicio {
    paralelo {
      entrada titulo esquerda durante 1.1s
      entrada subtitulo dissolver durante 1.35s
      entrada figura crescer durante 0.9s
    }
  }
  em destaque {
    pulso figura durante 0.8s
  }
  em encerramento {
    paralelo {
      saida titulo direita durante 1s
      saida subtitulo dissolver durante 1s
    }
  }
}
```

O compilador exige **uma instrução ou delimitador por linha**. A linguagem da 0.1 permanece compatível: `marca`, `em`, `sequencia`, `paralelo`, `esperar`, `mover`, `girar`, `escalar`, `animar`, `aparecer`, `desaparecer` e `efeito`. A 0.2 acrescenta `entrada ID ESTILO durante Ns`, `saida ID ESTILO durante Ns` e `pulso ID durante Ns`. Entradas: `dissolver`, `esquerda`, `direita`, `subir`, `descer`, `crescer`. Saídas: `dissolver`, `esquerda`, `direita`, `subir`, `descer`, `encolher`. Estilo combina deslocamento/opacidade/escala sem interpolador novo. Todas as ações são avaliadas em tempo absoluto; o compilador recusa IDs inexistentes, propriedades inválidas, conflitos na mesma propriedade e tempos fora do palco. Duração de ação ≤600 s; a camada GIL incorporada permanece limitada pelo esquema atual a 61 s.

`efeito ID` continua previsto no compilador original para áudio.tone, mas a camada de objeto GIL do Estúdio **rejeita cues**. Para áudio, utilize as faixas e fades existentes do mixer. Roteiro 0.2 ainda não sincroniza palavras da narração nem produz transição com sobreposição entre duas cenas.

## Biblioteca de estilos — 12 perfis originais

Editorial de dados, Neon técnico, Desenho de engenharia, Papel e tinta, Terminal/matriz, Cinema de arquivo, Biologia/microscopia, Tipografia brutalista, Âmbar e sombra, Quadrinhos, Televisor analógico e Art nouveau vegetal. São perfis de paleta, tamanhos tipográficos, geometria básica e programa de entrada/saída. São **novas implementações próprias**; não são cópias de assets, prompts ou os 341 estilos do Code Animation Prompts. Texturas reais, partículas volumétricas, morphing SVG e cinema procedural avançado permanecem fora desta etapa.

## Estudos utilizados, limites de integração e licenças

- `kaomei/stickman-video-director`: fluxo código vs. modelo, identidade visual, planejamento por cena/shot, assets reutilizáveis e QA de ação/continuidade. O código do Skill distingue gesto semântico de movimento decorativo (referência `b3-semantic-motion.md`). Ideias de fluxo **não justificam** importar o renderer, criar mais um player ou implantar geradores com custo.
- `XiaoyeCodes/code-animation-prompts`: catálogo com **341 orientações** e **196 imagens de referência**, selecionador offline, sistema de busca e renderização HTML por instante (`window.renderAt(t)`). O repositório informa **licenças mistas**, com exigência de redistribuição gratuita de parte da coleção. Por esse motivo **não incorporamos os assets originais**, e mantemos somente uma biblioteca inicial original com 12 perfis, sem copiar conteúdo protegido.
- `mankidev/antialgorithm`: `SKILL.md`, `scripts/seed.py` e `scripts/rough.py` orientam a evitar escolhas genéricas por meio de contexto e método visual. Aplicamos a ideia editorial de perfis com função, não a aleatoriedade do gerador de sementes na renderização determinística. Não incorporamos seu código.

Fontes consultadas em 17/11/2026: https://github.com/kaomei/stickman-video-director ; https://github.com/xiaoyecodes/code-animation-prompts ; https://github.com/mankidev/antialgorithm . Projetos de referência permanecem com seus respectivos autores e condições de uso; código novo do RD Studio é atribuído a Rogério Duarte.

## Testes obrigatórios antes de promover

1. Abrir a GUI em Chrome Android; botão Roteiro visível na navegação de composição em retrato e paisagem.
2. Escolher estilos diferentes e verificar que o texto muda visualmente, inclusive com acentos e caracteres Unicode.
3. `Compilar e visualizar` com marcações e ida/volta da linha temporal; verificar mudança de pose e ausência de recursos indisponíveis.
4. Confirmar que cancelar a inserção não altera a cena; inserir e salvar um objeto GIL; reabrir projeto e verificar a fonte persistida.
5. Importar o projeto ZIP `roteiro_estilos_03143.zip`, reproduzir todas as oito cenas, verificar precisamente a passagem 2→3 e exportar em navegador; comparar imagem e áudio.
6. Testar narração/áudio de clipes em projeto **pré-existente**, pois o projeto demonstrativo é propositadamente silencioso.
7. Verificar que HTML autônomo e apresentação executam o objeto GIL pelo runtime compartilhado. A correção de congelamento 2→3 e crossfade real ainda **não é dada como concluída**.

Não fazer commit/push até a revisão no Android. Reversão do patch com `--revert` e conferência dos hashes, sem `git reset` nem operações destrutivas.
