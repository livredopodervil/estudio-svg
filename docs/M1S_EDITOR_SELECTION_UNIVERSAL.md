# M1S — Selecao, camadas, modal e seletor

Implementado no modelo de objetos atual (image / video / gil):
- toque simples seleciona camada, toques repetidos na mesma posicao percorrem camadas visiveis
- imagens PNG com alfa sao consultadas por pixel antes da escolha (com fallback seguro)
- botão ⇄ seleciona o proximo objeto atras, mesmo quando existe sobreposicao
- ordem ↑ ↓ agora atualiza a prévia e informa posicao na pilha
- alcas/contornos limitados ao viewport; elementos ainda podem ser movidos para fora da cena
- modal Inserir: pesquisa, grupos recolhiveis, captura de rolagem e todos os exemplos GIL da biblioteca existente
- SVG usa a prévia ja existente, GIL usa a prévia dinamica existente, foto/video usa a propria visualizacao

Pendencias reais:
- O schema aceita apenas image, video, gil (ate 16), sem tipos group/instance. Não criar grupos persistentes sem migracao versionada do esquema e runtime.
- Hit-test do SVG da camada-base continua com o editor SVG existente; camadas GIL nao tem picking de todos os objetos internos.
- Detecção de alfa no pixel pode ser aproximada em imagens transformadas (rotacao/shear), podendo-se usar toques repetidos ou o botão ⇄.
- Cenas antigas nao sao reescritas.
- Revisão visual obrigatoria no Android antes do commit.

## Inicialização
`cd "$HOME/estudio_svg_v3_git" && RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh`

## Testes manuais
1. Abrir cena com duas imagens sobrepostas; tocar uma vez e repetir no mesmo ponto para selecionar a de tras.
2. Selecionar objeto GIL, tocar ⇄; seleção alterna sem mover objeto.
3. Tocar ↑ e ↓; a ordem muda na prévia imediatamente e persiste ao salvar.
4. Mover objeto até borda; alças não extrapolam viewport.
5. Abrir Inserir, rolar nas categorias; a página atrás deve permanecer imóvel.
6. Conferir 7 ou mais exemplos GIL no seletor, com prévia animada, além dos SVG, imagens e títulos.
7. Salvar/reabrir, prévia, exportação, e usar undo/redo nos objetos afetados.
