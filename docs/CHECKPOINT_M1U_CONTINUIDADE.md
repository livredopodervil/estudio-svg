# Checkpoint experimental M1P–M1U — 20261119T010213Z

- Branch de trabalho: `feat/studio-interface-m1b`.
- HEAD de origem: `5ccb0d258cdd2e183637c755535a3af912aaa3d4`.
- Consolidação de narração e legendas em lote, inspector, seleção, movimentos, grupos,
  instâncias compartilhadas, recursos e gerenciamento de projetos.
- Testes específicos invocados: 11; falhas: 2; indisponíveis: 0.
- **Checkpoint WIP**, não release validado. Logs em backup local fora do Git.
- Persistem pendências de auditoria M1j, navegação 3D e validação integral no Android.
- Não incluir arquivos `.bak.sha256`, caches, projetos pessoais ou artefatos de renderização.

## Comando para executar

```bash
cd "$HOME/estudio_svg_v3_git" || exit 1
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh
```

Abra a URL e a porta que o servidor efetivamente informar. Na porta 8771:
`http://127.0.0.1:8771/`.

## Revisão manual obrigatória nos próximos patches

- Abrir e salvar projeto com instâncias; conferir imagens e definições vinculadas.
- Substituir mídia base e verificar todas as instâncias.
- Abrir editor SVG e voltar ao mesmo projeto/cena.
- Renomear, mover à lixeira e restaurar projeto.
- Selecionar objetos transparentes, testar ordem de camadas e gizmos.
- Verificar legendas/áudio e exportação recuperável sem duração truncada.
- Investigar todos os testes com falha ou SKIP; não declará-los aprovados.
