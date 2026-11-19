# M1U — Recursos compartilhados, projetos e retorno do editor SVG

Objetivo: recurso selecionável, árvore hierárquica, substituição da mídia de uma definição vinculada, importação/exportação de definições JSON e operações seguras de projetos.

## Implementado
- Inspector M1T ampliado: visualização de instâncias, membros de grupos e biblioteca de definições.
- Substituição da imagem base altera todas as instâncias da definição, sem duplicar a mídia.
- Importar/exportar definições e grupos como JSON rd-studio-element-1, incluindo dependências do grafo. O JSON **não** inclui o arquivo binário da imagem: importe-a/substitua-a pelo inspector.
- Preservação do projeto e da cena ao voltar do editor SVG (URL e sessionStorage).
- Renomeação de projeto com validação e cópia exclusiva verificada. Exclusão é lixeira reversível já existente, acessível no navegador de projetos.
- Recuperação das imagens referenciadas exclusivamente por instance_library na importação ZIP, sem substituir arquivos existentes.
- Inventário inclui arquivos da biblioteca de instâncias.

## Limitações
- O importador de elementos JSON não incorpora binários. Faça upload da mídia base depois de importar quando necessário.
- Uma mídia GIL deve ser substituída pela importação de definição válida; não é permitido alterar hashes da fonte manualmente pelo inspector.
- Renomear um projeto não move arquivos de cache de voz: pode ser necessário regenerá-los. Projetos ativos e arquivados não devem ter nomes duplicados.
- O editor SVG continua sendo outro módulo; a navegação é mantida via URL/sessionStorage, com revisão visual obrigatória.
- O grafo 2D M1T preserva definições e grupos, mas a seleção interna de cada folha no viewport ainda é uma etapa futura.
- A recuperação ZIP cobre imagens JPEG/PNG/WebP de instâncias. Vídeos e sons GIL não são alterados.

## Testar no Android
```sh
cd "$HOME/estudio_svg_v3_git" || exit 1
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh
```
Abrir o endereço e a porta efetivamente informados pelo servidor, usualmente http://127.0.0.1:8771/.

1. Reimporte o ZIP demonstrativo M1U; confirme as quatro imagens presentes.
2. Abra Propriedades → Recursos, grupos e instâncias vinculadas. Selecione uma definição, substitua a imagem e confirme todas as instâncias alteradas.
3. Exporte um grupo como JSON, importe em outra cena e confirme as dependências e a prévia.
4. Edite o SVG de uma cena não inicial e volte: o mesmo projeto/cena deve continuar selecionado.
5. Abra Projetos, renomeie uma cópia de teste, envie-a à lixeira e restaure-a pela área de projetos arquivados.
6. Salve e recarregue; valide o arquivo original e a exportação de vídeo.

## Git e reversão
O instalador não cria stage, commit ou push. Seus backups ficam em `<gitdir>/rdstudio-backups/m1u-*`. Reversão `python rd_studio_m1u_aplicar.py rollback --repo "$PWD"` apenas se arquivos não forem modificados depois. Não usar `reset`, `clean` ou `push --force`. Fazer commit e push só após revisão visual no Android; preservar backups remotos.
