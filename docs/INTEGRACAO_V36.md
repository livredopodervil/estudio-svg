# Estúdio SVG — integração experimental V3.6

Autor do projeto: Rogério Duarte. Base: branch release/v3-alpha4-rc1, HEAD 86a6c6f, fotografia local `auditoria_estudio_20261114_044355.zip`. V3.4, exportador HTML autônomo e captura V3.5 encontrados; os dois últimos continham mudanças não confirmadas. Esta revisão não altera esses módulos de voz/exportação/captura, nem mídias, projetos, site remoto ou histórico Git.

## Rotas e voz

- O serviço do editor fornece `/player-v3/?project=<identificador>` e os módulos canônicos do Player. O editor salva o projeto antes de abrir a página, no mesmo host e porta. O botão de retorno conserva o identificador. Um hash SHA-256 do projeto normalizado associa o JSON e os SVGs. Se o JSON mudar durante a reprodução, reabra o Player. O hash não versiona o conteúdo dos arquivos de mídia externos.
- `/api/player-v3` entrega o JSON e as URLs de voz disponíveis. Uma requisição por cena entrega o SVG-base com marcadores para a timeline nativa. Não há PNGs nem série pré-renderizada por cena. O antigo player estático continua funcionando no formato publicado anterior. O navegador ainda depende de decodificadores compatíveis para clipes.
- `/captura` usa o renderizador Python por meio da prévia, como antes. Opções: voz do navegador (padrão), mix WAV e sem áudio. Compartilha o Narrator da V3.4; a timeline retém a cena até a conclusão da fala. O modo browser não inclui a música do mix. Se não houver tradução, fala o texto no idioma original. Tradução automática e persistência completa de pacotes multilíngues não fazem parte desta revisão.
- Corrigida rota ausente `/media-recorder-v35.js`. O gerador estático experimental passa a copiar o Player canônico em vez de reconstruí-lo com patches antigos.

## Camadas

Campo opcional `camadas` da cena: mapa de `imagem`, `conteudo`, `cabecalho`, `titulo`, `subtitulo`, `rodape` para `{z,dx,dy,oculta}`. Exemplo: `{"imagem":{"z":100,"dx":30,"dy":0,"oculta":false}}`. `dx,dy` são unidades lógicas da cena (largura lógica 1280), `z` crescente na direção do observador. Quando omitido, conserva a composição visual anterior; o SVG contém novos grupos de seleção. A composição editada ocorre sobre o fundo decorativo; o vídeo sobreposto continua em sua camada separada, acima da cena. A ordem dentro de uma camada de conteúdo procedural ou de uma cena espacial continua definida pelo renderizador original.

O painel da prévia seleciona múltiplas camadas e objetos SVG por ID. Escopo global aplica por tipo de camada ou ID (IDs repetidos entre cenas devem representar objetos equivalentes). Mover SVG usa coordenadas locais do pai. Ordenar SVG opera dentro do mesmo pai, sem quebrar hierarquia. Ocultar preserva o objeto; excluir SVG remove o elemento da composição, sem excluir mídia ou arquivos. O histórico de desfazer é local à sessão do painel e recusa a reversão quando a cena sofreu outra edição. Animações associadas a IDs excluídos permanecem no JSON (sem alvo visível). Salvar persiste tudo no projeto. O Ateliê SVG continua disponível para edição fina e criação de IDs. Não inclui drag/resize genérico, edição individual de primitivas procedurais, manipulação 3D ou reordenação de clipes para trás da cena.

A prévia, HTML autônomo e MP4 usam `graphics.visualize`; o Player V3 usa a base desse renderizador e o seu motor JS. Não há prova de paridade pixel a pixel de todas as animações procedurais. A cache visual inclui o JSON da cena e o hash de graphics.py, podendo haver regeneração do cache.

## Verificação

`python -m unittest discover -s tests -p 'test_v36_integration.py' -v`; `node tests/test_layers_v36.mjs`; `python -m unittest discover -s tests -v`. No Android: escolher projeto não demo; salvar; abrir Player V3; alternar voz browser/gravada; testar Apresentar sem preparar mix; mover imagem em todas as cenas, salvar/reabrir e conferir HTML e MP4. Testar câmera/microfone e observar o limite de áudio do navegador.
