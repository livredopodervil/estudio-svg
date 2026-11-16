# RD Studio 5 / GIL Timeline 0.2.0 (experimental)
Autoria principal: Rogério Duarte. Assistência: OpenAI GPT. A partir do RD Studio 4.4.2 recuperado em 14/11/2026 e do laboratório GIL 0.1. Nenhum motor original substituído. O nome RD Studio 5 é provisório; a numeração GIL permanece compatível com a DSL 0.1.

**Versão atual:** siga [docs/AUTHORING_V020.md](docs/AUTHORING_V020.md). As descrições abaixo da 0.1.1/0.1.2 registram marcos históricos, não substituem o novo fluxo de exportação e publicação.

## Rodar (Termux)
Extraia o ZIP em um diretório novo, execute a partir da pasta `rd_studio_gil_v01`:

```
python tools/check_base.py "$HOME/rd-studio"
node --test gil/tests/*.test.mjs
PYTHONPATH="$PWD/rdstudio" python -m unittest discover -s rdstudio/tests -v
python -m unittest discover -s tests -v
python tools/launch.py --site "$HOME/rd-site-skill-home-uykhyf4m/site" --video "$HOME/estudio_svg_v3_git"
```

O caminho do site é um checkout histórico para teste; confirme o diretório real, não publique a partir dessa versão antiga. O inicializador não instala nada e encerra somente seus próprios processos. Portas: 8875 admin, 8876 prévia, 8791 GIL, 8784 Estúdio SVG. Se algum serviço já estiver aberto, encerre-o normal (Ctrl+C). Pode omitir `--video` para iniciar só os outros serviços. A aba Multimídia abre cada módulo numa nova origem local, sem encaminhar tokens/admin APIs.

## Produzir páginas
No GIL, edite a fonte ou propriedades e use a seção Publicar composição como página. O código atual do campo de texto é validado ao exportar, inclusive rascunho ainda não aplicado; o usuário recebe um pacote `.rdpatch.zip` add-only. O pacote contém `projetos/<id>/index.html`, opcionalmente `player.html` autocontido, `projeto.gil.txt` e `assets/video.mp4`. O player é sandboxado sem acesso à origem pai. O MP4 tem controles independentes do GIL. O limite de 8 MiB por MP4 e 12 MiB por ZIP é do RD Patch original; não foi ampliado. Assinatura ftyp não é validação completa do codec. Não há upload direto, sincronização GIL/MP4, exportação MP4 no GIL, nem WebGL nativo.

Baixe o pacote no navegador. No RD Studio, Pacotes IA → Examinar → Aplicar → Prévia → Vistoria → Git. Escolha um ID novo para não substituir páginas. Projetos existentes continuam intactos; para reaplicar uma revisão ao mesmo ID, será necessário criar um futuro pacote replace contra hashes reais. O mecanismo existente permite remover somente arquivos do pacote que não tenham sido editados depois. O demo incluído tem player de 30 s e MP4 silencioso de 5 s produzido por amostragem do renderer SVG + CairoSVG + FFmpeg (não é exportador integrado). `gil/tools/sample_frames.mjs` e `build_demo.mjs` documentam a geração.

## Publicação Git
Use `tools/prepare_publication.py --prepare-source "$HOME/estudio_svg_v3_git"` para criar worktree sobre a branch remota `release/v3-alpha4-rc1`, com destino `feature/rd-studio-gil-v01`. O código ficará dentro de `integrations/rd-studio-gil-v01/`. Não inclui alterações locais da V3.6 automaticamente. Não sobrescreve branch de integração preexistente. Para preparar demo no site, `python tools/prepare_publication.py --prepare-demo "$HOME/rd-site-v3-release-b48ozlrr/site"`. O comando busca `main` remota e cria outro worktree, adicionando apenas arquivos sob `projetos/gil-timeline-v01/`. A homepage continua intacta. O script imprime o caminho para revisão e o comando de publicação explicitamente opt-in `--publish ... --confirm-rights`. Consulte o conteúdo de `publication.json` fora do worktree. Use apenas após revisão da autoria/licenças, inspeção do worktree e testes; `--confirm-rights` é confirmação do usuário, não uma licença concedida pelo código. A publicação do demo usa commit + push normal, recusa avanço remoto e não altera outros worktrees. Não executa merge/reset ou force push. Se push falhar depois de commit, preserve o worktree e inspecione o Git em vez de refazer indiscriminadamente.

Não foi achado um LICENSE no snapshot recebido do SpatialSeed; não confundir código público com licença de redistribuição irrestrita. As fontes pinadas têm proveniência em `gil/PROVENIENCIA.json`; confirme direitos e preservação de créditos antes da publicação. Não escolher licença por conta do autor. O manifest `PACKAGE.json` identifica os arquivos exatos do kit, sem credenciais nem configurações de projeto; não é assinatura criptográfica.

## Arquitetura
O RD Studio original administra arquivos e projetos. O GIL Timeline (`language`, `model`, `timeline`) desenvolve objetos arbitrários, o player usa o mesmo serviço de domínio e os mesmos adaptadores `render-svg`/`audio`. O novo `page-export` é um adaptador puro: recebe fonte validada, metadados e bytes MP4, produz manifesto e ZIP. `page-ui` traduz intenção do usuário. A interface não recebe acesso à escrita no site/Git; a única autoridade de instalação é o PatchManager original. O gerador de player compartilha módulos pinados, sem implementar outra gramática ou outra avaliação temporal. O RD Studio mantém preview em origem separada. A biblioteca GIL é uma etapa experimental; o editor não está conectado ao sandbox/comandos canônicos do SpatialSeed e não substitui o Estúdio SVG. A integração via API compartilhada e projeção WebGL fica para etapa posterior.

## Validação
47 testes RD Studio originais, 26 testes GIL e exportador, 2 testes integração (aplica/remove RD Patch, igualdade byte a byte da base). Teste Chromium do player exportado: SVG, seek, play/pause, viewport 390px. Execução Android, serviços simultâneos e publicação GitHub real ainda não verificados. O MP4 demo tem duração confirmada por ffprobe. O laboratório anterior pode continuar a ser usado offline; o composer de pacotes requer servidor local HTTP em loopback ou HTTPS, com Web Crypto.

Teste adicional: player autocontido em iframe sandbox `allow-scripts` carregou SVG no Chromium; fluxos Git de preparação e publicação de fonte/site foram exercitados em dois repositórios bare locais simulados, com guard de URL substituído apenas no teste, sem acesso real a GitHub, e alterações locais preexistentes preservadas.

## Atualização incremental 0.1.2
Veja [docs/WORKSPACE.md](docs/WORKSPACE.md): unidade de componentes, exemplo Máquina cinética, exportação MP4 offline, novas rotas de acesso e correção de prévia. As instruções de preparação/publicação 0.1.1 acima são históricas: use o helper atualizado, que exige V3.6 devidamente consolidada e que prepara somente a nova demonstração. Os worktrees históricos não são bases de publicação para a revisão atual. Não publique arquivos fora do manifesto.
