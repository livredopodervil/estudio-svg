# RD Studio · M1a — composição central, sem mudança de runtime

Base auditada: commit Git `01b5761` (`checkpoint-v3134-experimental`), branch `feat/viewport-03130`.
Autoria original: Rogério Duarte. Preservam-se os créditos e as licenças dos demais componentes.

## Objetivo e mudanças
- Um único viewport central e a timeline original sempre visível, inclusive no celular.
- Cenas, propriedades e produção são painéis laterais recolhíveis, acessíveis pelo mesmo cabeçalho de composição.
- Uma barra de ícones compactos no Android. A barra flutuante de transformação anterior permanece, mas só aparece quando a composição estiver ativa e nenhum painel lateral/biblioteca estiver aberto.
- Ações SVG/imagem/camadas antigas passam para a seção **Ferramentas avançadas**, sem remover seus handlers.
- Os botões principais de importação/exportação JSON e ZIP ficam no menu `Mais`; Salvar e abrir projetos permanecem no cabeçalho.
- A biblioteca continua utilizando os dois formatos existentes (SVG com faixas e GIL nativa). Ao escolher SVG, agora exige prévia geométrica e confirmação antes da mutação. As quatro fontes GIL testadas aparecem como cartões de entrada no seletor existente, com prévia temporal naquele seletor.
- IDs e nós originais foram preservados. O novo script reaproveita os eventos e funções já implementados, sem criar motor de renderização, mixagem ou transporte.

## Restrições e trabalho subsequente
Esta etapa **não** unifica a estrutura de documento SVG/GIL, não adiciona efeitos novos ou títulos, não corrige a transição audiovisual congelada na exportação e não resolve o clipe de câmera preto. A melhoria visual do M1a é separada das tarefas M2-M6.

A inserção de SVG em cena não-SVG ainda exige selecionar **Criar nova cena** na biblioteca, por limitação do modelo existente. Nenhuma inserção muda isso silenciosamente. Exemplos GIL experimentais que não compilaram no player continuam identificados abaixo dos cartões testados; não são tratados como compatíveis.

## Critérios de revisão no Android
1. Abrir projeto antigo e confirmar áudio, vídeo, salvar e timeline.
2. Retrato/paisagem: viewport central; painel Cenas abre e fecha sem sair da composição.
3. Biblioteca SVG: tocar cartão abre prévia, fechar não altera a cena; confirmar insere somente quando compatível.
4. Biblioteca GIL: tocar cartão abre uma prévia animada no seletor existente, não insere automaticamente.
5. Menu Inserir permite selecionar mídia e ver prévia, sem criar outra cena.
6. Propriedades mostra inspetor do objeto selecionado, ou o editor da cena quando nada está selecionado.
7. Áudio e Produção aparecem como painéis, sem esconder a timeline; a barra flutuante some fora da composição.
8. Desfazer/refazer, salvar, reabrir e exportar vídeo curto com áudio e overlay.

## Arquivos alterados
`app.py`, `web/app.js`, `web/index.html`, `AGENTS.md`;
arquivos novos `web/studio-layout-v1.js`, `web/studio-layout-v1.css`, `tests/test_studio_layout_m1.py`, `docs/INTERFACE_M1A.md`.

## Reversão
Use o comando `python apply.py --video <checkout> --revert` do pacote aplicado, desde que os hashes ainda sejam os desta revisão. Nenhum commit ou push automatizado.
