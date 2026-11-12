# V2.7.2 — Transformações, animações e música contínua

- Ateliê: rotação por alça ou campo numérico, espelhamento ao cruzar o limite da alça de escala; lixeira visível; alças somente na ferramenta Selecionar; estilos sólido, tracejado, pontilhado e traço-ponto, largura ajustável.
- Editor avançado retirado da interface; código e arquivos de terceiros preservados.
- Compositor de imagem: enquadramento e dimensão da foto manipuláveis; modelo de quadro ou fundo escolhido diretamente na janela.
- Animações por objeto SVG (ID) ou fotografia de cena: translacao, rotacao, escala e fade. JSON validado e interpolação idêntica na prévia e no MP4.
- Trilha global contínua opcional: mixagem após concatenar os áudios, sem reiniciar nas mudanças de cena. Música específica da cena continua independente.
- Projetos existentes mantêm o modo antigo de áudio (trilha_continua=false) e a estrutura original de SVG.

## Limitações explícitas
- As animações atuam sobre objetos SVG identificados por `id`, `__imagem__`, `__titulo__`, `__subtitulo__` e `__conteudo__` (o agrupamento gráfico gerado pela cena).
- A prévia individual de uma cena não inclui a trilha global contínua (ela aparece no mix completo e no MP4 final).
- A taxa `draw_fps` continua limitando a suavidade temporal da exportação conforme o projeto.
