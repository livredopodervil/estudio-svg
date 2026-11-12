# Estúdio SVG — correção V2.7.4.1

Base: V2.7.4, branch `feat/v27-editor-imagens`. Não há alteração do esquema JSON.

- **Remover vídeo da cena:** desvincula `video_clipe.arquivo` sem apagar o arquivo de mídia. O áudio da cena permanece intacto; salvar o projeto é uma operação separada.
- **Apresentação com clipe:** `/captura` reproduz o `video_clipe` na mesma posição, tamanho, enquadramento, opacidade e momento da cena usados na prévia. A trilha sonora permanece sob controle do elemento de áudio da apresentação, evitando duplicar o som do clipe.
- **Apresentação limpa:** a barra e a dica desaparecem durante a reprodução. Um toque no quadro mostra temporariamente os comandos para interromper. Ao parar, os comandos voltam a ser exibidos.
- **Tela vertical ou horizontal:** o quadro da apresentação respeita a proporção do projeto. A saída MP4 do renderizador não foi alterada.

## Testes

- `python -m unittest discover -s tests -q`
- `node --check web/app.js && node --check web/captura.js` (se Node disponível).
- Testar no Android: remover clipe e salvar/reabrir, apresentar cenas com e sem vídeo, mudar para 9:16, alternar tela cheia e conferir que a barra não aparece no vídeo gravado.

O uso de gravação de tela pelo Android e a captura de áudio interno dependem do navegador, do Android e do gravador. Para entrega final reproduzível, prefira Renderizar MP4.
