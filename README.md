# Estúdio SVG V2.6 — Ateliê Vetorial

## O que foi corrigido

A V2.5 dependia da disponibilidade de `editor.canvas.getSvgString()` no SVG-Edit 7.4.2. Em determinadas instalações, a referência ao canvas é `editor.svgCanvas`; o erro exibido era **“Não foi possível ler o desenho do SVG-Edit”**. Na V2.6, o **Ateliê SVG é o editor padrão**, opera diretamente sobre elementos SVG nativos no navegador e serializa o documento sem depender de APIs privadas ou variáveis do SVG-Edit. O SVG-Edit continua disponível como opção avançada, com adaptador de compatibilidade para `svgCanvas`/`canvas`, caso o pacote externo esteja instalado.

A interface foi reconstruída com textos de alto contraste, comandos identificáveis, área de desenho clara, painel de camadas e inspetor de propriedades. Em aparelhos estreitos, a navegação alterna entre **Camadas**, **Desenho** e **Propriedades**. O editor principal **não precisa de Node.js nem baixar um projeto externo**.

## Instalação no Termux

Baixe `estudio_svg_termux_v26_COMPLETO.zip` para Downloads e execute:

```bash
set -e
unzip -o "$HOME/storage/downloads/estudio_svg_termux_v26_COMPLETO.zip" -d "$HOME"
cd "$HOME/estudio_svg_v26"
bash instalar.sh
python app.py verificar
python app.py servir --port 8771
```

Abra `http://127.0.0.1:8771` no mesmo aparelho. Se a porta 8771 estiver ocupada, escolha outra porta livre com `--port 8772` (o endereço também muda). Não pare os serviços nas portas 8765, 8766, 8769 ou 8770. O servidor só atende a conexão local 127.0.0.1.

O instalador importa projetos e mídias da V2.5/V2.4/V2.3/V2.2 **sem sobrescrever projetos existentes**. A V2.6 tem pasta de instalação independente. A instalação inicial não é necessária para a biblioteca SVG-Edit, pois o Ateliê SVG usa recursos nativos do navegador.

## Uso do editor

1. Abra um projeto no Estúdio, escolha uma cena de tipo `SVG`, ou use `+ SVG` para criá-la.
2. Clique em **Abrir Ateliê SVG · camadas**.
3. Escolha uma ferramenta: selecionar, retângulo, elipse, linha, caneta livre ou texto.
4. Arraste na área de desenho (ou toque, no caso de texto) para criar o objeto.
5. Toque no objeto para selecioná-lo, arraste para movê-lo e altere cor, tamanho, opacidade e coordenadas no painel Propriedades.
6. Organize camadas, alterando seus nomes, visibilidade, bloqueio e ordem.
7. Clique em **Salvar cena**. O Estúdio é avisado da modificação. O cache de outras cenas é preservado.

### Arquivos e formatos

- **Abrir SVG**: importa arquivo vetorial, mantendo as camadas e objetos de formas compatíveis. A importação substitui a ilustração corrente; salve antes se quiser preservá-la.
- **Imagem**: insere PNG, JPEG, WebP, GIF (primeiro quadro) ou BMP em uma camada SVG, convertida localmente para PNG e com limite de tamanho. Fotografias continuam rasterizadas.
- **Exportar**: salva o documento atualmente editado como SVG, PNG, JPEG ou WebP. Exportação SVG é vetorial; os outros formatos são rasterizados pelo navegador em 1280 × 720.
- **Código**: permite acessar e editar a serialização SVG completa, com validação.
- **Avançado**: abre o SVG-Edit 7 instalado anteriormente para ferramentas adicionais, quando o componente está disponível. O SVG-Edit preserva sua própria interface; a V2.6 não altera a aparência interna dessa biblioteca.

### Atalhos

- Ctrl+S: salvar cena.
- Ctrl+Z: desfazer.
- Ctrl+Shift+Z: refazer.
- Delete: remover objeto selecionado.

### O que o editor nativo ainda não oferece

O Ateliê nativo atende à edição de cenas vetoriais comuns, com objetos, camadas, inserção de imagens, seleção, movimentação, formas, texto, SVG livre e exportação. **Não é um substituto integral do Inkscape**: não tem edição de nós Bézier, álgebra complexa de caminhos, filtros com interface completa ou edição de gradientes por pontos de controle. Para essas funções, use o botão **Avançado** (SVG-Edit), importe SVG criado em outro aplicativo ou edite o código SVG. A renderização com ImageMagick pode divergir de filtros e animações exibidos pelo navegador.

## Renderização e áudio

Todos os comandos da V2.5 continuam disponíveis:

```bash
cd "$HOME/estudio_svg_v26"
python app.py audio --projeto arcabouco_fiscal_2026
python app.py render-leve --projeto arcabouco_fiscal_2026
python app.py cache-status --projeto arcabouco_fiscal_2026
```

Use `--sem-voz` no renderizador para gerar visualização sem locuções prontas. Os vídeos são copiados para a pasta Movies do Android. O editor vetorial não refaz automaticamente a narração; o cache das outras cenas não é invalidado quando uma só ilustração muda.

## Diagnóstico

Se abrir uma versão antiga, feche a aba anterior e abra `http://127.0.0.1:8771`, usando uma nova aba anônima para evitar cache do navegador. Certifique-se de que o servidor V2.6 esteja em execução no Termux.

Se a exportação PNG/JPEG/WebP falhar em um SVG com filtros complexos, primeiro exporte como SVG e remova efeitos ou imagens externos não incorporados. Para um teste mínimo, crie um retângulo e exporte PNG. Se o arquivo SVG apresentar elementos descartados, use **Código** e confira a sanitização de segurança: scripts, links de rede e `foreignObject` são removidos pelo servidor.

Se o servidor informar **“A cena foi alterada em outra aba”**, recarregue a cena para obter a versão mais recente; não sobrescreva projetos concorrentes.

## Testes

```bash
cd "$HOME/estudio_svg_v26"
python -m unittest discover -s tests -v
```

Oito testes Python passaram nesta distribuição. No Chromium, foram verificados editor aberto, desenho de retângulo, exportação SVG e PNG e chamada de salvamento, em telas desktop e mobile. Os testes visuais de navegador utilizaram um servidor API simulado, e a integração do backend foi testada separadamente. A operação no Android/Termux ainda precisa ser confirmada no aparelho.

## Componentes externos

- SVG-Edit 7.4.2: https://github.com/SVG-Edit/svgedit (opcional e legado na V2.6).
- FFmpeg: https://ffmpeg.org/
- Pillow: https://pillow.readthedocs.io/
- Edge-TTS: https://github.com/rany2/edge-tts

Os avisos de licença das bibliotecas instaladas separadamente permanecem em suas distribuições.


## Atualização experimental 2.7 (branch Git isolada)

A V2.7 adiciona um botão **SVG** no cabeçalho, acesso direto ao Ateliê SVG na prévia,
**imagem opcional em qualquer tipo de cena**, seleção visual de uma foto dentro de uma
prancha e reposicionamento/redimensionamento no quadro. Em telas verticais, o tipo
`cartoes` procura uma área sem sobreposição entre a imagem e os cartões de texto.

O editor vetorial usa **um dedo** para desenhar/selecionar e **dois dedos** para
ampliar/reduzir e deslocar a prancheta. O gesto de navegação não é salvo dentro do
SVG nem acrescentado ao histórico de desenho. **Ajustar** restaura a visualização.

O editor de fotografia é **não destrutivo**: a mídia original é preservada em `midia/`,
o recorte relativo (`imagem.crop`) e a posição/tamanho relativos (`x`, `y`, `w`, `h`)
são salvos por cena no JSON. A mesma imagem importada pode ser reutilizada em
outras cenas sem duplicar o arquivo. `modo: fundo` estende a imagem ao quadro;
`modo: quadro` a posiciona como cartão independente.

A branch de desenvolvimento deve ser instalada em um **worktree próprio**, sem
sobrescrever a V2.6. Para servir esse worktree em uma porta livre:

```bash
cd "$HOME/estudio_svg_v27_git"
python app.py verificar
python -m unittest discover -s tests -p 'test_*.py' -v
python app.py servir --port 8772
```

Acesse `http://127.0.0.1:8772`. Faça a validação no Android antes de integrar
qualquer alteração na branch `main`. Não existe publicação remota automática.

## Atualização experimental 2.7.2 — transformações, animações e áudio

Na branch `feat/v27-editor-imagens`, o Ateliê permite girar pelo controle acima da seleção, espelhar por redimensionamento cruzando o canto oposto, excluir objetos pelo botão **Excluir**, e escolher espessura e estilo de linha (**Contínua**, **Tracejada**, **Pontilhada**, **Traço-ponto**). As alças ficam ocultas nas ferramentas de desenho. O botão legado **Avançado** não é mais exibido; os arquivos e as licenças externos não foram apagados.

Em **Cena → Animações**, adicione efeitos temporais aos objetos SVG identificados por `id`, ao fragmento de fotografia (`__imagem__`), ao título (`__titulo__`), subtítulo (`__subtitulo__`) ou conteúdo gráfico (`__conteudo__`). Cada efeito pode transladar, girar, escalar ou alterar a opacidade entre `inicio` e `fim`, valores normalizados de 0 a 1. A taxa de estados SVG por segundo (`draw_fps`) controla a suavidade do MP4.

Em **Projeto → Trilha global contínua**, habilite a música ao longo de todo o vídeo. Por padrão, projetos legados mantêm a trilha reiniciada por cena. Quando a opção está ativa, o Estúdio concatena o áudio das cenas, mistura a trilha global depois, e respeita a opção de atenuar a música durante a locução. Trilhas específicas de cena permanecem independentes. A prévia de uma única cena não inclui a trilha global contínua; use **Mixar áudio** ou renderize o vídeo inteiro para ouvi-la corretamente.

A **Imagem da cena → Recortar e posicionar** aceita pranchas com várias fotos. Selecione o modo **Quadro móvel / ajustável** para redimensionar o fragmento pelos quatro cantos; o modo **Fundo inteiro** ocupa todo o quadro. A mídia original não é sobrescrita.

A V2.7.2 deve ser aplicada somente após pré-validação do instalador de patch, no worktree de desenvolvimento. Execute os testes e valide os gestos no Android antes de registrar um commit. A documentação anterior descreve a V2.6 e é preservada para referência histórica.

## V2.7.3: vídeo e captura local

A partir de uma cena, use **Importar vídeo** (MP4/WebM/MOV/MKV/M4V) ou **Gravar câmera**. Em Áudio, escolha **Gravar narração**; a gravação exige permissão explícita. O JSON da cena possui `video_clipe`, cujo arquivo está em `midia/`. Vídeos são sobrepostos no quadro SVG e seu áudio é opcional, vinculado por `audio.voice_file`.

Abra uma cena SVG pelo editor para adaptar a prancheta ao 9:16. A conversão de viewBox só se torna permanente ao salvar. Use **Animações → Inspecionar animação no tempo** e o botão de exemplo para visualizar fade e translação.
