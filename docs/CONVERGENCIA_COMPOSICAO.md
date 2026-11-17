# Direção arquitetural: composição e projeções
Autoria do projeto: Rogério Duarte. Direção discutida para evolução posterior; não descreve funcionalidades já implementadas.

## Objetivo
Uma composição é um documento de objetos identificáveis, recursos, relações, propriedades e funções do tempo, com ações e eventos tipados. A representação persistente não depende de SVG, HTML, Canvas, WebGL, FFmpeg ou de um formato de vídeo. Geometria, mídia, interfaces, páginas, sons e roteiros são tipos de recursos com semântica própria, não sinônimos de malha. Os objetos podem ter projeções visuais, sonoras e interativas distintas.

## Regras de convergência
- Preservar fonte e versão de linguagem. Inicialmente, leitores/adaptadores de GIL3, GIL timeline, documentos SpatialSeed e JSON Estúdio geram descritores para a evolução temporal comum; não descartar recursos ainda sem projeção.
- Um único estado de documento, identidade de ocorrência e relógio lógico. Grupos, referenciais, transformações afins e propriedades animáveis devem ser reutilizáveis entre mídia e geometria. Perspectiva e deformação não linear exigem contratos próprios.
- Interfaces e HTML podem ser objetos estruturais com filhos, eventos e projeção DOM; som pode ser um grafo de fontes e efeitos; roteiro opera sobre propriedades, ações e tempo, sem execução arbitrária de código.
- Reutilizar o runtime e contratos do SpatialSeed quando comprovadamente adequados, fixando versão e preservando licenças. Não copiar implementações nem abrir outro editor em iframe para simular integração.
- Viewport, hierarquia, timeline e inspetor são visões do mesmo documento e da mesma seleção.

## Entrega imediata
V3.12: caminho experimental de exportação no navegador usando Canvas, MediaRecorder e mix nominal. Ainda depende de Python para a arte base e o áudio, e não resolve a fusão das linguagens nem o viewport unificado. A evolução para WebGL e aplicação estática deve preservar esse caminho funcional e os projetos existentes.
