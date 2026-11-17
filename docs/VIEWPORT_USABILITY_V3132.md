# V3.13.2 — navegação e histórico (experimental)

O histórico geral cobre alterações do documento após `dirtyNow`, com até 64 checkpoints ou 16 MiB, em memória da aba; não substitui o histórico do editor vetorial externo. O navegador de projetos utiliza pastas *virtuais* por navegador (localStorage), sem mover JSON ou mídias, e um filtro de nomes. Nenhuma alteração de pastas no servidor. A barra do viewport é movível pela alça dedicada. Clicar/tocar um objeto seleciona; duplo clique/toque abre o inspetor.

Os exemplos oferecidos na janela de importação foram reduzidos a composições locais, silenciosas e verificáveis pelo runtime. Exemplos incompatíveis não são apagados, continuam em `examples/components` e podem ser convertidos depois, quando o motor GIL incorporar eventos sonoros.

A edição interativa, exportação, manipulação e mixagem antigas permanecem; não há alteração nos formatos dos documentos.
