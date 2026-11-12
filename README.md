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
