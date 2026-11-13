# Estúdio SVG V3 Alpha 2 — mídias portáteis e hierarquia espacial

Experimental. A `main` V2.7.4.1 é a referência estável e não é modificada.

- Compositor de imagens: importar nova prancha e nomeá-la, criar cópia com outro nome e ajustar crop por oito alças ou movendo o retângulo.
- Produção: ZIP exportável com `projetos/<nome>.json`, `midia/<arquivos referenciados>` e LEIA-ME. Não inclui mídias que não sejam usadas no projeto; recusa mídias ausentes ou pacote maior que 250 MB. Importação do ZIP é manual, via extração em uma cópia do repositório.
- Áudio: remover todas as faixas de uma cena e silenciar também a trilha global contínua apenas no intervalo correspondente. Gravações originais não são apagadas.
- Compositor espacial: cilindros, cones e grupos de transformação, hierarquia `pai` de objetos e faixa `__camera__/azimute` (elevacao, distancia também aceitos via JSON). A mesma projeção alimenta a prévia e a exportação.
- Não há cópia de código nem acoplamento ao runtime do SpatialSeed: a API espacial é uma implementação experimental própria, com contrato JSON limitado e validado.

## Reversão

Antes de editar ou confirmar novos commits, use `git apply -R --check` seguido de `git apply -R` com o patch do pacote. Não use `git reset --hard`.
