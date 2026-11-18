# RD Studio M1b — seleção legada, títulos e fonte GIL

Base exigida: M1a (V3.14.0) aplicada sobre checkpoint `01b5761`, branch `feat/studio-interface-m1a`. Mudanças incrementais, sem formatos de projeto adicionais.

## Recursos

1. **Imagem original:** tocar a imagem no viewport ou a entrada da timeline mostra «Converter imagem em camada editável». Após confirmação, o arquivo original é preservado e o objeto independente pode ser movido, escalado, girado e animado; o campo original `imagem.arquivo` fica vazio. Uma imagem com recorte ativo bloqueia essa conversão para evitar mudança visual silenciosa. Imagem de fundo convertida passa a sobrepor a arte base, com aviso explícito.
2. **SVG com ID:** arraste direto do elemento no viewport; alças permitem escala uniforme e rotação. A fonte `cena.svg` é modificada em memória e seu histórico recebe a mudança; objetos sem ID, cenas não SVG e alvos gerados por outros renderizadores continuam a usar seus editores próprios. A manipulação não reescreve os programas `animacoes` do documento.
3. **Títulos:** oito estilos de PNG com fundo transparente, miniaturas na biblioteca, texto e subtítulo configuráveis e prévia. Ao confirmar, o título é inserido como `objetos_midia` de tipo `image`; animações de entrada reutilizam `motionSource` e o Timeline GIL. O editor, Player V3, HTML autônomo e exportador continuam usando o mesmo fluxo de imagem. O texto não é um vetor independente: alterações regeneram o PNG, preservando a identificação da camada.
4. **Editor GIL:** acessível diretamente no Estúdio, sem redirecionamento para a porta 8791. Compila e pré-visualiza fontes com o runtime GIL instalado, permitindo alterar a fonte da cena/camada existente ou inserir fonte validada no diálogo de objetos. Não converte GIL3.

## Não resolvido neste marco

- Acesso a elementos sem ID e transformação 3D são futuros contratos.
- Tipografia preservada como nós de texto editáveis dentro de GIL/SpatialSeed, não PNG, depende de desenho canônico e compartilhado entre todos os exportadores.
- Transições de cena, quadros congelados, vídeos pretos e exportação de longa duração ainda exigem regressões específicas.
- A renderização depende da disponibilidade de `RD_GIL_ROOT`; o instalador de M1b exige o caminho explícito na execução do servidor.

## Testes de aceitação no Android

1. Abrir biblioteca e conferir oito estilos com miniaturas. Gerar título com texto próprio, escolher entrada, confirmar e verificar o resultado na prévia e na timeline.
2. Arrastar título, redimensionar pelas alças, trocar animação no inspetor e validar desfazer/refazer e persistência após salvar/reabrir.
3. Selecionar imagem original, converter, arrastar e girar. Testar imagem com recorte e verificar bloqueio seguro.
4. Em cena SVG com IDs, tocar uma forma e arrastar, escalar e girar. Salvar, reabrir e inspecionar o SVG resultante.
5. Abrir «Editar fonte GIL aqui», pré-visualizar, editar e aplicar sem abrir porta adicional.
6. Comparar prévia, Apresentar, HTML autônomo e exportação de um projeto curto com título+clipe+áudio. Não considerar aprovado até a verificação real.
