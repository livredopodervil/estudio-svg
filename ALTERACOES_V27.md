# V2.7 — patch incremental experimental

Base prevista: `main` em `ec65000`, incluindo o patch local de gestos V2.6.1.

Arquivos afetados: `app.py`, `schema.py`, `graphics.py`, `projeto.schema.json`,
`web/index.html`, `web/app.js`, `web/style.css`, `web/vetor.*`, com um módulo novo
`web/image-composer.js` e testes. O conteúdo da V2.6 e os arquivos de mídia locais
não são substituídos.

Ajustes:
- Ateliê SVG explicitamente acessível; preservados os recursos anteriores.
- Navegação de dois dedos capturada no palco, inclusive em áreas fora dos objetos.
- Imagem opcional como cartão móvel ou fundo em todos os tipos de cena.
- Recorte de atlas visual com arraste, tamanho e posição por cena.
- Composição de cartões melhorada para 9:16, inclusive celulares em paisagem.
- Back-end com endpoint local restrito para visualização de imagens já importadas.
- Manutenção dos modelos de dados anteriores e testes adicionais.

Ainda requer validação em Android físico, com dois dedos reais, antes de merge.
