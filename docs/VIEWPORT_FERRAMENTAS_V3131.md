# Viewport V3.13.1 — ferramentas de toque

Base: V3.13.0 experimental, sem mudança do documento nem dos serviços.

- Barra persistente no canto superior esquerdo do palco, com ícones para Inserir, Selecionar, Mover, Escalar, Girar, Cisalhar, Pivô e Propriedades.
- Um toque seleciona a ferramenta; arrastar um objeto usa a transformação selecionada. Em Selecionar, as alças existentes continuam disponíveis. Em Escalar/Girar/Cisalhar/Pivô, a alça relevante permanece visível e funcional; o gesto livre atua sobre a superfície do objeto.
- Os controles aparecem também no Modo Foco. Os números do inspetor continuam editáveis e alterações são persistidas apenas ao salvar. Não há manipulação de áudio ou alteração de duração.
- Testes automatizados: álgebra affine/dragPose no Node; interação DOM isolada no Chromium. A experiência móvel e a composição com o áudio exigem revisão no Android.
- Limitação: a barra funciona inicialmente para `objetos_midia` independentes. Objetos dentro da fonte GIL e clipes legados ainda mantêm seus próprios editores.
