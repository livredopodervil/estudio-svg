# M1T — Grafo de definições, grupos e instâncias 2D

**Status:** etapa experimental, opt-in; código independente da linguagem de roteiro e do motor GIL, mas integrado à normalização de projeto, à prévia DOM e ao renderizador de navegador. **Não é uma migração automática** dos objetos antigos. O editor gráfico de filhos internos e o adaptador SpatialSeed 3D ficam para o próximo marco.

## Continuidade e base

Manter o repositório e a branch reais confirmados por `git rev-parse`. Preservar todos os arquivos e projetos existentes. O M1T adiciona dois módulos JavaScript, um normalizador Python e um painel recolhível na região de propriedades. As mudanças nos outros módulos são inserções localizadas que recusam âncoras divergentes. Não fazer push antes do teste visual no Android.

## Modelo

O projeto aceita uma biblioteca compartilhada de definições:

```json
{
  "instance_library": {
    "format": "rd-instance-library-1",
    "definitions": [
      {"id":"foto","kind":"media","media":{"id":"foto","kind":"image","file":"foto.jpg","x":0.5,"y":0.5,"w":0.35,"h":0.35,"start":0,"end":8}},
      {"id":"grupo","kind":"group","children":[
        {"id":"esquerda","ref":"foto","transform":{"matrix":[1,0,0,1,-0.2,0]}},
        {"id":"direita","ref":"foto","transform":{"matrix":[1,0,0,1,0.2,0]}}
      ]}
    ]
  }
}
```

Uma cena inclui `instances:[{"id":"r1","ref":"grupo","transform":{"matrix":[1,0,0,1,0,0]},"start":0,"end":8}]`.

Uma **definição** descreve um objeto visual reutilizável ou grupo. Uma **aresta** referencia uma definição e inclui sua transformação. Uma **instância de cena** coloca esse objeto no espaço e no tempo; alterações na definição propagam-se a todas as instâncias que a referenciam. As definições são armazenadas uma vez no JSON. O navegador ainda cria elementos DOM distintos para cada folha, e a economia real de memória de decodificação não foi medida.

A matriz afim `[a,b,c,d,e,f]` representa o operador

`x' = ax + cy + e`, `y' = bx + dy + f`.

Os operadores são compostos na ordem hierárquica pai × filho. Em pixels, a matriz é convertida usando a largura e altura reais do viewport para preservar rotações, escalas, cisalhamento e translações também em 9:16. `pixelMatrix` implementa essa conversão para a prévia e para o Canvas de exportação.

## Interface M1T

Abra uma cena e selecione uma **imagem**, um **vídeo sem áudio** ou uma **composição GIL independente**. Em Propriedades, expanda **Grupos e instâncias vinculadas (M1T)**. Use **Criar instância do selecionado**; os controles permitem mover, girar, escalar, cisalhar, duplicar e remover a instância. Com duas ou mais instâncias no mesmo intervalo, é possível agrupá-las em uma definição reutilizável. A edição profunda dos filhos e o picking do conteúdo instanciado diretamente sobre o viewport ainda não foram implementados.

A ordem das raízes no array determina a ordem entre instâncias; as instâncias são desenhadas depois dos objetos independentes existentes. A ordenação unificada com todos os tipos de cena permanece para outro marco.

## Segurança e limites

IDs: `[A-Za-z0-9_-]`, até 64 caracteres. Até 64 definições, 32 arestas por grupo, 32 raízes por cena e 128 folhas visuais expandidas. Referências inexistentes, ciclos, matrizes singulares e campos não finitos são recusados. Vídeos instanciados precisam ter áudio desativado até que a mixagem por instância esteja implementada. Não se avalia JavaScript vindo dos projetos.

A gramática do roteiro 0.4 permanece existente: o planejador futuro deve emitir o mesmo `instance_library` + `instances` por operações transacionais, sem inventar um segundo motor temporal.

## Comandos e validação

```bash
cd "$HOME/estudio_svg_v3_git" || exit 1
python "$HOME/storage/downloads/rd_studio_m1t_aplicar.py" check --repo "$PWD"
python "$HOME/storage/downloads/rd_studio_m1t_aplicar.py" apply --repo "$PWD"
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh
```

Se o servidor confirmar a porta 8771: `http://127.0.0.1:8771/`.

Teste o ZIP demonstrativo: importar, reproduzir e confirmar quatro imagens com apenas duas definições; mover uma instância pelo painel e salvar/reabrir. Reproduzir o projeto anterior sem campos de instância para garantir compatibilidade. Testar exportação pelo navegador e, quando disponível, o modo offline recuperável. Verificar que o som dos vídeos com áudio não é silenciosamente descartado (inserção recusada). Não publicar antes de revisar no Android.

## Próxima etapa

M1T-1: seleção do elemento instanciado na cena, edição de hierarquia por árvore, arraste/gizmo único, ordenação conjunta, animações nos nós de grupo e instâncias, recursos de personagens, adaptador espacial 3D e bindings do console/GIL para as definições.

## Reversão

`python "$HOME/storage/downloads/rd_studio_m1t_aplicar.py" rollback --repo "$PWD"` antes de commitar. A reversão recusa arquivos modificados depois da aplicação. Ela não apaga projetos nem dados do usuário. Após commit, usar novo commit Git de reversão, preservando o histórico remoto.
