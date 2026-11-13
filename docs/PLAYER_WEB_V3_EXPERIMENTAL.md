# Player Web V3 — experimental

Autor do projeto: Rogério Duarte.

O publicador experimental `tools/estudio_svg_v3_integrador.py`
usa `graphics.visualize` para gerar um SVG base por cena;
`web_player/v3/runtime.js` implementa a timeline e a projeção espacial
diretamente no navegador. Narração e pivô são preservados do Player V2.

A demonstração hospedada no site pessoal é uma exportação estática;
não requer Termux ou `/api/preview` para executar.

Limites: vídeos sobrepostos, trilha musical e equivalência visual integral
com o MP4 ainda não comprovados. Não remover versões estáveis.

Reprodução local: gerar em `$HOME/estudio_player_stage/vetorial-v3`
com o publicador, servir a raiz do stage por HTTP.
Os scripts dos protótipos V1/V2 são incluídos em `tools/`
quando presentes no Downloads local.
