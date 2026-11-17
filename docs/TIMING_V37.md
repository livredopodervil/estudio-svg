# Estúdio SVG V3.7 experimental — controle de tempo e mídia

Base: V3.6 (7e93c3b7d45cec366d4c2ddbd91f3a7a235bdafc) com ponte GIL 0.2.1 aplicada. Ajuste local ao Estúdio SVG, sem alterações no RD Studio ou SpatialSeed.

## Duração em lote

Cenas → Durações em lote. Escopo: todas, selecionada ou intervalo inclusivo (numeração a partir de 1). Piso só eleva valores menores; Fixar atribui uma duração; Multiplicar usa um fator sobre cada duração. Validação da transação inteira no intervalo 0,5–600 s, sem limitar silenciosamente. Prévia do total nominal antes da edição. Um desfazer local do último lote, até mudança do projeto / conflito de duração. A ação altera apenas `duracao`, não arquivos nem faixas de áudio, posição de objetos ou fontes GIL. Salvar persiste. A duração final do render pode diferir devido ao encaixe da fala e FPS de desenho. Se a narração exceder, escolha explicitamente Estender a cena. Diminuir a duração de cena pode terminar a visualização de um clipe antes do fim, sem modificar o arquivo original. Aumentar não retemporaliza um clipe GIL: use a opção de repetir no clipe se desejar.

## Velocidade

Prévia muda seu relógio visual e a taxa do clipe (sem áudio na prévia); Player V3 muda o relógio visual e a taxa de cada clipe. O controle de voz existente continua independente; a taxa efetiva da voz é o produto das duas taxas, limitado pelo Narrator (0,6–2,2). No Web Speech, a taxa de uma fala corrente não pode ser alterada dinamicamente; a próxima fala usa a nova taxa. Ao aguardar uma narração longa, o Player também congela o clipe no ponto da timeline. Apresentar permite escolher a velocidade antes de Iniciar; mix WAV usa playbackRate, voz do browser usa a taxa efetiva. Não muda FPS, MP4 renderizado, arquivos TTS, ou JSON de projeto por mera mudança de velocidade de reprodução. Esta revisão não adiciona o mixer de efeitos/música ao Player V3 (os clipes permanecem mudos; utilize Apresentar com Mix WAV ou renderize MP4 para ouvir o mix completo).

## Correção de clipes

`StudioMedia` segue o relógio do Player em `tick`, atualiza após metadata e seek, pausa ao aguardar voz, descarta promessas antigas na troca de cena, e esconde clipe não repetitivo quando termina como o renderizador. A fonte GIL continua preservada no JSON, mas a projeção usada pelo vídeo é o clipe MP4 derivado, não a execução nativa GIL. `HEAD` das rotas de clipe e voz fornece o comprimento e o tipo MIME reais; GET/Range permanece. O status do clipe mostra o arquivo, duração e erros de carregamento. Serve para distinguir mídia ausente ou incompatibilidade de codec de uma falha temporal. Atualize a página depois de reiniciar o servidor. Publicações estáticas anteriores precisam ser reconstruídas separadamente.

## Testes

103 testes Python na cópia reconstruída (RD_GIL_ROOT apontando para GIL 0.2.1), 8 testes JavaScript incluindo camadas. Chromium móvel de 390 px: editor completo com APIs simuladas — piso, desfazer, multiplicação, salvar referência de voz, prévia 2×; Player completo com SVGs reais e clipes MP4 originais das cenas 12 e 14 do projeto Jones Manoel, servidos por Blob com fetch de teste — seek, execução 1,5×, pausa. HTTP local HEAD, GET/Range, erro 404 e caminho inválido testados separadamente. A validação integrada por HTTP no navegador Android e qualidade/tempo da voz física permanecem pendentes. Não há alteração do esquema de projeto.
