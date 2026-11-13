# Estúdio Player Web — regras de manutenção

- Autoria dos projetos Estúdio SVG e SpatialSeed: Rogério Duarte. Conservar histórico, documentação e licenças de terceiros.
- O Estúdio mantém JSON e mídias originais; o player público é apenas leitura e consome manifestos `studio.web-player/v1`.
- Não executar scripts, HTML ou código JavaScript proveniente do JSON/SVG de um projeto. Imagens SVG entram como `img.src`, nunca `innerHTML`.
- Não modificar `main`, `index.html`, `js/site-v10.js`, `modules/manifest.json`, `modules/graph.js`, CNAME, serviços e aplicações externas sem conferir a árvore atual e obter autorização.
- Todo patch deve ser incremental, reversível, com testes de compatibilidade e sem exclusões incidentais.
- O SpatialSeed só está integrado via renderização espacial pré-computada pelo Estúdio; runtime interativo e scripts não fazem parte desta versão.
- Para publicação, travar os commits dos repositórios e verificar hashes dos recursos; não vender sincronização por GitHub como tempo real.
- Testar UI móvel, áudio, legendas, vídeo e o portal 3D após a instalação em branch candidata.
