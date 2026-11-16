# GIL Timeline — laboratório isolado

Autoria principal: Rogério Duarte. Assistência: OpenAI GPT.

- Este laboratório não é uma nova autoridade sobre o documento SpatialSeed, Estúdio SVG ou RD Studio. Não editar os repositórios originais por meio deste pacote.
- Ler README, PROVENIENCIA.json e testes antes de alterações. Manter parser, domínio, tempo, projeção, áudio e UI separados. Toda mutação vai por DocumentService; seleção e avaliação temporal são transitórias. Recursos arbitrários sem adaptador permanecem estruturados e são diagnosticados.
- Reutilizar interfaces públicas, não importar estado interno dos renderizadores. Não duplicar parser matemático, matrizes ou runtime temporal. A cópia pinada em vendor é uma dependência de teste; futura integração deve receber os módulos do SpatialSeed por interface de importação, com revisão verificada.
- Não reescrever GIL3 nem declarar compatibilidade sintática completa. Preservar fontes/variantes legadas. Não executar código livre de um projeto; expressão matemática restrita não é JavaScript. Não elevar capabilities implícitas.
- Atualizações cirúrgicas e acompanhadas por testes. Não commit/push/publicação sem autorização. Não incluir tokens, dados privados ou configurações de repositórios. Não mover código experimental para produção sem gates.
